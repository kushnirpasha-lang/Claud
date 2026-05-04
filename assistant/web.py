import asyncio
import json
import os
import threading
import time
import uuid

from flask import Flask, jsonify, request, send_from_directory

import claude_client

app = Flask(__name__, static_folder="static")

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "static", "uploads")
VPS_URL = f"http://{os.environ.get('SSH_HOST', '188.166.67.237')}"

_ig_lock = threading.Lock()
_IG_SESSIONS_FILE = os.path.join(os.path.dirname(__file__), "ig_sessions.json")


def _load_sessions() -> dict:
    try:
        with open(_IG_SESSIONS_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_sessions(sessions: dict) -> None:
    try:
        with open(_IG_SESSIONS_FILE, "w") as f:
            json.dump(sessions, f)
    except Exception:
        pass


_ig_sessions: dict[str, dict] = _load_sessions()

_tg_auth_state: dict = {}
_tg_auth_lock = threading.Lock()


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    session_id = (data.get("session_id") or "default").strip()

    if not message:
        return jsonify({"error": "Empty message"}), 400

    try:
        reply = claude_client.chat(f"web_{session_id}", message)
        return jsonify({"reply": reply})
    except Exception as exc:
        print(f"Web chat error: {exc}")
        return jsonify({"error": "Service error, try again"}), 500


@app.route("/api/new", methods=["POST"])
def new_chat():
    data = request.get_json(silent=True) or {}
    session_id = (data.get("session_id") or "default").strip()
    claude_client.clear(f"web_{session_id}")
    return jsonify({"ok": True})


@app.route("/api/tg-auth/request", methods=["POST"])
def tg_auth_request():
    try:
        from telethon import TelegramClient
    except ImportError:
        return jsonify({"error": "telethon not installed"}), 500

    api_id   = int(os.environ.get("TELEGRAM_API_ID", 0))
    api_hash = os.environ.get("TELEGRAM_API_HASH", "")
    phone    = "+380637353733"

    async def _request():
        c = TelegramClient("/opt/assistant/user_session", api_id, api_hash)
        await c.connect()
        if await c.is_user_authorized():
            await c.disconnect()
            return {"status": "already_authorized"}
        sent = await c.send_code_request(phone)
        with _tg_auth_lock:
            _tg_auth_state["hash"]  = sent.phone_code_hash
            _tg_auth_state["phone"] = phone
        await c.disconnect()
        return {"status": "code_sent", "phone": phone}

    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(_request())
    loop.close()
    return jsonify(result)


@app.route("/api/tg-auth/signin", methods=["POST"])
def tg_auth_signin():
    try:
        from telethon import TelegramClient
        from telethon.errors import SessionPasswordNeededError
    except ImportError:
        return jsonify({"error": "telethon not installed"}), 500

    data  = request.get_json(silent=True) or {}
    code  = (data.get("code") or "").strip()
    if not code:
        return jsonify({"error": "code required"}), 400

    api_id   = int(os.environ.get("TELEGRAM_API_ID", 0))
    api_hash = os.environ.get("TELEGRAM_API_HASH", "")

    with _tg_auth_lock:
        phone      = _tg_auth_state.get("phone", "+380637353733")
        phone_hash = _tg_auth_state.get("hash", "")

    if not phone_hash:
        return jsonify({"error": "call /api/tg-auth/request first"}), 400

    async def _signin():
        c = TelegramClient("/opt/assistant/user_session", api_id, api_hash)
        await c.connect()
        try:
            await c.sign_in(phone, code, phone_code_hash=phone_hash)
            me = await c.get_me()
            return {"status": "success", "name": me.first_name, "username": me.username}
        except SessionPasswordNeededError:
            return {"status": "2fa_required"}
        except Exception as e:
            return {"status": "error", "detail": str(e)}
        finally:
            await c.disconnect()

    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(_signin())
    loop.close()

    if result.get("status") == "success":
        os.system("systemctl restart assistant &")

    return jsonify(result)


@app.route("/api/instagram/session-create", methods=["POST"])
def instagram_session_create():
    data = request.get_json(silent=True) or {}
    session_id = (data.get("session_id") or "").strip()
    image_url = (data.get("image_url") or "").strip()
    caption = (data.get("caption") or "").strip()
    if not session_id or not image_url:
        return jsonify({"error": "session_id and image_url required"}), 400
    filename = f"{session_id}.jpg"
    with _ig_lock:
        _ig_sessions[session_id] = {
            "image_url": image_url,
            "filename": filename,
            "caption": caption,
            "created_at": time.time(),
        }
        _save_sessions(_ig_sessions)
    return jsonify({"ok": True, "session_id": session_id})


@app.route("/api/instagram/prepare", methods=["POST"])
def instagram_prepare():
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400
    f = request.files["file"]
    image_bytes = f.read()
    if not image_bytes:
        return jsonify({"error": "empty file"}), 400
    mime_type = (f.content_type or "image/jpeg").strip()
    user_hint = (request.form.get("hint") or "").strip()

    ext = os.path.splitext(f.filename or "photo.jpg")[1].lower() or ".jpg"
    filename = uuid.uuid4().hex + ext
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as fp:
        fp.write(image_bytes)
    image_url = f"{VPS_URL}/static/uploads/{filename}"

    try:
        caption = claude_client.generate_instagram_caption(image_bytes, mime_type, user_hint)
    except Exception as e:
        caption = ""

    session_id = uuid.uuid4().hex
    with _ig_lock:
        _ig_sessions[session_id] = {
            "image_url": image_url,
            "filename": filename,
            "caption": caption,
            "created_at": time.time(),
        }
        _save_sessions(_ig_sessions)

    preview_url = f"{VPS_URL}/instagram/preview/{session_id}"
    return jsonify({"session_id": session_id, "preview_url": preview_url, "caption": caption})


@app.route("/instagram/preview/<session_id>")
def instagram_preview_page(session_id):
    with _ig_lock:
        exists = session_id in _ig_sessions
    if not exists:
        return "Сессия не найдена или истекла", 404
    return send_from_directory("static", "instagram_preview.html")


@app.route("/api/instagram/session/<session_id>", methods=["GET"])
def instagram_session_get(session_id):
    with _ig_lock:
        s = _ig_sessions.get(session_id)
    if not s:
        return jsonify({"error": "not found"}), 404
    return jsonify({"image_url": s["image_url"], "caption": s["caption"]})


@app.route("/api/instagram/session/<session_id>/post", methods=["POST"])
def instagram_session_post(session_id):
    with _ig_lock:
        s = _ig_sessions.get(session_id)
    if not s:
        return jsonify({"error": "not found"}), 404

    import requests as req_lib
    gh_token = os.environ.get("MY_PAT", "")
    payload = {
        "event_type": "instagram_publish",
        "client_payload": {
            "session_id": session_id,
            "image_url": s["image_url"],
            "caption": s["caption"],
        }
    }
    r = req_lib.post(
        "https://api.github.com/repos/kushnirpasha-lang/Claud/dispatches",
        json=payload,
        headers={"Authorization": f"token {gh_token}", "Accept": "application/vnd.github.v3+json"},
        timeout=10,
    )
    if r.status_code not in (200, 204):
        return jsonify({"error": f"Failed to trigger workflow: {r.text}"}), 500

    with _ig_lock:
        _ig_sessions[session_id]["status"] = "publishing"
        _save_sessions(_ig_sessions)
    return jsonify({"ok": True, "status": "publishing"})


@app.route("/api/instagram/session/<session_id>/mark-result", methods=["POST"])
def instagram_session_mark_result(session_id):
    data = request.get_json(silent=True) or {}
    with _ig_lock:
        if session_id not in _ig_sessions:
            return jsonify({"error": "not found"}), 404
        if data.get("ok"):
            _ig_sessions[session_id]["status"] = "published"
            _ig_sessions[session_id]["post_id"] = data.get("id", "")
        else:
            _ig_sessions[session_id]["status"] = "error"
            _ig_sessions[session_id]["error"] = data.get("error", "unknown")
        _save_sessions(_ig_sessions)
    return jsonify({"ok": True})


@app.route("/api/instagram/session/<session_id>/status", methods=["GET"])
def instagram_session_status(session_id):
    with _ig_lock:
        s = _ig_sessions.get(session_id)
    if not s:
        return jsonify({"status": "not_found"}), 404
    return jsonify({
        "status": s.get("status", "ready"),
        "post_id": s.get("post_id", ""),
        "error": s.get("error", ""),
    })


@app.route("/api/instagram/session/<session_id>/regen", methods=["POST"])
def instagram_session_regen(session_id):
    with _ig_lock:
        s = _ig_sessions.get(session_id)
    if not s:
        return jsonify({"error": "not found"}), 404
    try:
        filepath = os.path.join(UPLOAD_DIR, s["filename"])
        with open(filepath, "rb") as fp:
            image_bytes = fp.read()
        caption = claude_client.generate_instagram_caption(image_bytes, "image/jpeg", "")
        with _ig_lock:
            _ig_sessions[session_id]["caption"] = caption
            _save_sessions(_ig_sessions)
        return jsonify({"caption": caption})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/instagram/session/<session_id>/update", methods=["POST"])
def instagram_session_update(session_id):
    data = request.get_json(silent=True) or {}
    caption = (data.get("caption") or "").strip()
    with _ig_lock:
        if session_id not in _ig_sessions:
            return jsonify({"error": "not found"}), 404
        _ig_sessions[session_id]["caption"] = caption
        _save_sessions(_ig_sessions)
    return jsonify({"ok": True})


@app.route("/api/instagram/session/<session_id>/cancel", methods=["DELETE"])
def instagram_session_cancel(session_id):
    with _ig_lock:
        _ig_sessions.pop(session_id, None)
        _save_sessions(_ig_sessions)
    return jsonify({"ok": True})


def run() -> None:
    port = int(os.environ.get("WEB_PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
