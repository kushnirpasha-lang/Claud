import asyncio
import os
import threading
import uuid

from flask import Flask, jsonify, request, send_from_directory

import claude_client

app = Flask(__name__, static_folder="static")

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


UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

VPS_URL = os.environ.get("VPS_URL", "http://188.166.67.237")


@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "empty filename"}), 400
    ext = os.path.splitext(f.filename)[1].lower() or ".jpg"
    filename = uuid.uuid4().hex + ext
    f.save(os.path.join(UPLOAD_DIR, filename))
    url = f"{VPS_URL}/static/uploads/{filename}"
    return jsonify({"url": url, "filename": filename})


@app.route("/instagram")
def instagram_page():
    return send_from_directory("static", "instagram.html")


@app.route("/api/instagram/info", methods=["GET"])
def instagram_info():
    try:
        import instagram_client
        info = instagram_client.get_account_info()
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/instagram/post", methods=["POST"])
def instagram_post():
    data = request.get_json(silent=True) or {}
    image_url = (data.get("image_url") or "").strip()
    caption = (data.get("caption") or "").strip()

    if not image_url:
        return jsonify({"error": "image_url required"}), 400

    try:
        import instagram_client
        result = instagram_client.post_photo(image_url, caption)
        return jsonify({"ok": True, "id": result.get("id")})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/drive/setup", methods=["POST"])
def drive_setup():
    try:
        import google_drive_client
        result = google_drive_client.create_product_structure()
        return jsonify({"ok": True, "folders": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/drive/upload", methods=["POST"])
def drive_upload():
    """Upload image to Drive product folder (Исходники or Обработанные)."""
    product = request.form.get("product", "").strip()
    size = request.form.get("size", "").strip()
    folder_type = request.form.get("folder_type", "Исходники").strip()
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400
    f = request.files["file"]
    image_bytes = f.read()
    mime_type = f.content_type or "image/jpeg"
    name = f.filename or None
    try:
        import google_drive_client
        file_id = google_drive_client.upload_to_product(product, size, folder_type, image_bytes, mime_type, name)
        return jsonify({"ok": True, "file_id": file_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/drive/process", methods=["POST"])
def drive_process():
    """Crop image to Instagram format and save to Обработанные."""
    product = request.form.get("product", "").strip()
    size = request.form.get("size", "").strip()
    ig_format = request.form.get("format", "1:1").strip()
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400
    f = request.files["file"]
    image_bytes = f.read()
    try:
        import image_processor
        import google_drive_client
        processed = image_processor.crop_to_instagram(image_bytes, ig_format)
        file_id = google_drive_client.upload_to_product(product, size, "Обработанные", processed, "image/jpeg")
        return jsonify({"ok": True, "file_id": file_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/drive/list", methods=["GET"])
def drive_list():
    """List files in product/size/folder_type."""
    product = request.args.get("product", "").strip()
    size = request.args.get("size", "").strip()
    folder_type = request.args.get("folder_type", "Обработанные").strip()
    try:
        import google_drive_client
        files = google_drive_client.list_product_files(product, size, folder_type)
        return jsonify({"files": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/drive/file/<file_id>", methods=["GET"])
def drive_file(file_id):
    """Download a file from Drive."""
    try:
        import google_drive_client
        from flask import Response
        image_bytes = google_drive_client.download_file(file_id)
        return Response(image_bytes, mimetype="image/jpeg")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/drive/post-to-instagram", methods=["POST"])
def drive_post_to_instagram():
    """Make Drive file public → post to Instagram → move to Выложенные → remove public access."""
    data = request.get_json(silent=True) or {}
    file_id = (data.get("file_id") or "").strip()
    caption = (data.get("caption") or "").strip()
    mime_type = (data.get("mime_type") or "image/jpeg").strip()
    if not file_id:
        return jsonify({"error": "file_id required"}), 400
    try:
        import google_drive_client
        import instagram_client
        public_url = google_drive_client.make_file_public(file_id)
        result = instagram_client.post_photo(public_url, caption)
        posted_name = google_drive_client.move_file_to_posted(file_id, mime_type)
        google_drive_client.remove_public_access(file_id)
        return jsonify({"ok": True, "instagram_id": result.get("id"), "posted_as": posted_name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def run() -> None:
    port = int(os.environ.get("WEB_PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
