import asyncio
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

import claude_client

app = Flask(__name__, static_folder="static")

_tg_auth_state: dict = {}
_tg_auth_lock = threading.Lock()

# ── Агентный дашборд: хранилище ─────────────────────────────────────────────

DATA_DIR = Path("/opt/assistant/data")
EVENTS_FILE = DATA_DIR / "events.jsonl"
DASHBOARD_TOKEN = os.environ.get("DASHBOARD_TOKEN", "")


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _append_event(event: dict) -> None:
    _ensure_data_dir()
    with open(EVENTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _read_all_events() -> list[dict]:
    if not EVENTS_FILE.exists():
        return []
    events = []
    with open(EVENTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                pass
    return events


# ── Основной чат ─────────────────────────────────────────────────────────────

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


# ── Агентный дашборд: эндпоинты ──────────────────────────────────────────────

@app.route("/agents")
def agents_dashboard():
    return send_from_directory("static", "agents.html")


@app.route("/dashboard")
def new_dashboard():
    return send_from_directory("static", "dashboard.html")


@app.route("/api/agents/stream")
def api_stream():
    project = request.args.get("project")
    agent_filter = request.args.get("agent")
    last_ts = request.args.get("since", "")

    def generate():
        current_last = last_ts
        import time
        while True:
            all_events = _read_all_events()
            new_events = [
                e for e in all_events
                if e.get("ts", "") > current_last
                and (not project or e.get("project") == project)
                and (not agent_filter or e.get("agent") == agent_filter)
            ]
            for e in new_events:
                current_last = max(current_last, e.get("ts", ""))
                yield f"data: {json.dumps(e, ensure_ascii=False)}\n\n"
            time.sleep(1.5)

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/events", methods=["POST"])
def receive_event():
    if DASHBOARD_TOKEN:
        token = request.headers.get("X-Token", "")
        if token != DASHBOARD_TOKEN:
            return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    if not data.get("ts"):
        data["ts"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    if not data.get("task_id"):
        data["task_id"] = str(uuid.uuid4())[:8]

    _append_event(data)
    return jsonify({"ok": True})


@app.route("/api/agents/projects")
def api_projects():
    all_events = _read_all_events()

    projects: dict[str, dict] = {}
    for e in all_events:
        proj = e.get("project") or "unknown"
        if proj not in projects:
            projects[proj] = {
                "name": proj,
                "active_agent": None,
                "last_event": None,
                "recent_events": [],
            }
        p = projects[proj]
        p["last_event"] = e
        p["recent_events"].append(e)
        etype = e.get("type", "")
        if etype in ("start", "step"):
            p["active_agent"] = e.get("agent")
        elif etype in ("complete", "error"):
            p["active_agent"] = None

    result = []
    for name, p in projects.items():
        result.append({
            "name": name,
            "active_agent": p["active_agent"],
            "last_event": p["last_event"],
            "recent_events": p["recent_events"][-5:],
        })

    result.sort(key=lambda x: x["last_event"]["ts"] if x["last_event"] else "", reverse=True)
    return jsonify(result)


@app.route("/api/agents/events")
def api_events():
    project = request.args.get("project")
    agent = request.args.get("agent")
    since = request.args.get("since", "")
    limit = min(int(request.args.get("limit", 100)), 500)

    all_events = _read_all_events()

    filtered = []
    for e in all_events:
        if project and e.get("project") != project:
            continue
        if agent and e.get("agent") != agent:
            continue
        if since and e.get("ts", "") <= since:
            continue
        filtered.append(e)

    return jsonify(filtered[-limit:])


@app.route("/api/agents/stats")
def api_stats():
    all_events = _read_all_events()
    projects = set(e.get("project") for e in all_events if e.get("project"))
    return jsonify({
        "total_events": len(all_events),
        "total_projects": len(projects),
        "last_event_ts": all_events[-1]["ts"] if all_events else None,
    })


# ── Telegram авторизация ──────────────────────────────────────────────────────

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


def run() -> None:
    port = int(os.environ.get("WEB_PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
