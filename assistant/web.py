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


_AGENTS_HTML = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>HairLove — Agent System</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #0a0a14; color: #e8e8f0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; min-height: 100vh; overflow: hidden; }
  .header { display: flex; align-items: center; justify-content: space-between; padding: 16px 28px; border-bottom: 1px solid rgba(255,255,255,0.07); background: rgba(255,255,255,0.02); }
  .header-brand { display: flex; align-items: center; gap: 10px; font-size: 15px; font-weight: 600; }
  .header-brand .dot { width: 8px; height: 8px; background: #a78bfa; border-radius: 50%; box-shadow: 0 0 8px #a78bfa; animation: pulse 2s infinite; }
  .header-time { font-size: 13px; color: #6b7280; font-variant-numeric: tabular-nums; }
  .header-status { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #10b981; background: rgba(16,185,129,0.1); padding: 4px 10px; border-radius: 20px; border: 1px solid rgba(16,185,129,0.2); }
  .header-status::before { content: ''; width: 6px; height: 6px; background: #10b981; border-radius: 50%; animation: pulse 2s infinite; }
  .canvas { position: relative; width: 100vw; height: calc(100vh - 57px); }
  svg.lines { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 1; }
  .line { stroke: rgba(167,139,250,0.25); stroke-width: 1.5; fill: none; stroke-dasharray: 6 4; animation: dash 20s linear infinite; }
  .line.active { stroke: rgba(167,139,250,0.55); stroke-width: 2; }
  @keyframes dash { to { stroke-dashoffset: -100; } }
  .node { position: absolute; transform: translate(-50%, -50%); z-index: 10; cursor: pointer; }
  .node-center { left: 50%; top: 50%; }
  .node-center .card { width: 140px; background: linear-gradient(135deg, #1e1b4b, #312e81); border: 2px solid #6366f1; border-radius: 20px; padding: 20px 16px; text-align: center; box-shadow: 0 0 40px rgba(99,102,241,0.3), 0 0 80px rgba(99,102,241,0.1); transition: all 0.2s; }
  .node-center .card:hover { box-shadow: 0 0 60px rgba(99,102,241,0.5); transform: scale(1.03); }
  .node-center .avatar { width: 52px; height: 52px; background: linear-gradient(135deg, #6366f1, #a78bfa); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px; margin: 0 auto 10px; box-shadow: 0 0 20px rgba(167,139,250,0.4); }
  .node-center .name { font-size: 14px; font-weight: 700; color: #fff; }
  .node-center .role { font-size: 10px; color: #a5b4fc; margin-top: 3px; text-transform: uppercase; letter-spacing: 1px; }
  .node .card { width: 148px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 14px 12px; text-align: center; transition: all 0.2s; backdrop-filter: blur(10px); }
  .node .card:hover { background: rgba(255,255,255,0.08); border-color: rgba(167,139,250,0.5); transform: scale(1.04); box-shadow: 0 0 30px rgba(167,139,250,0.15); }
  .node .icon { font-size: 28px; margin-bottom: 6px; display: block; }
  .node .agent-name { font-size: 12px; font-weight: 600; color: #e2e8f0; margin-bottom: 3px; }
  .node .agent-cmd { font-size: 10px; color: #6366f1; font-family: monospace; margin-bottom: 6px; }
  .node .agent-desc { font-size: 10px; color: #94a3b8; line-height: 1.4; margin-bottom: 8px; }
  .node .badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 600; }
  .badge-active { background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.3); }
  .badge-pending { background: rgba(107,114,128,0.15); color: #9ca3af; border: 1px solid rgba(107,114,128,0.2); }
  .badge-building { background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.3); }
  .node-texts { left: 22%; top: 22%; }
  .node-insta { left: 78%; top: 22%; }
  .node-strategy { left: 14%; top: 50%; }
  .node-site { left: 86%; top: 50%; }
  .node-competitors { left: 22%; top: 78%; }
  .node-ads { left: 78%; top: 78%; }
  .detail-panel { position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); background: rgba(15,15,30,0.95); border: 1px solid rgba(255,255,255,0.1); border-radius: 14px; padding: 14px 20px; font-size: 12px; color: #94a3b8; z-index: 20; backdrop-filter: blur(20px); display: flex; gap: 24px; align-items: center; white-space: nowrap; }
  .detail-panel .hint { display: flex; align-items: center; gap: 6px; }
  .detail-panel .hint span { color: #e2e8f0; }
  .kbd { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15); padding: 2px 6px; border-radius: 5px; font-size: 11px; font-family: monospace; color: #a78bfa; }
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
  .tooltip { position: absolute; background: rgba(15,15,30,0.97); border: 1px solid rgba(167,139,250,0.3); border-radius: 10px; padding: 10px 14px; font-size: 11px; color: #cbd5e1; pointer-events: none; z-index: 100; min-width: 200px; display: none; }
  .tooltip.show { display: block; }
  .tooltip .t-title { color: #a78bfa; font-weight: 600; margin-bottom: 6px; font-size: 12px; }
  .tooltip .t-row { display: flex; justify-content: space-between; gap: 12px; margin-top: 4px; }
  .tooltip .t-label { color: #6b7280; }
  .pulse-ring { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); width: 180px; height: 180px; border: 1px solid rgba(99,102,241,0.2); border-radius: 50%; pointer-events: none; z-index: 0; animation: ring-pulse 3s ease-out infinite; }
  .pulse-ring:nth-child(2) { animation-delay: 1s; }
  .pulse-ring:nth-child(3) { animation-delay: 2s; }
  @keyframes ring-pulse { 0% { transform: translate(-50%, -50%) scale(1); opacity: 0.5; } 100% { transform: translate(-50%, -50%) scale(2.5); opacity: 0; } }
</style>
</head>
<body>
<div class="header">
  <div class="header-brand"><div class="dot"></div>HairLove Agent System</div>
  <div class="header-status">Система активна</div>
  <div class="header-time" id="clock">--:--:--</div>
</div>
<div class="canvas" id="canvas">
  <div class="pulse-ring"></div><div class="pulse-ring"></div><div class="pulse-ring"></div>
  <svg class="lines" id="lines"></svg>
  <div class="node node-center">
    <div class="card"><div class="avatar">👤</div><div class="name">Павел</div><div class="role">Orchestrator</div></div>
  </div>
  <div class="node node-texts" data-id="texts">
    <div class="card"><span class="icon">✍️</span><div class="agent-name">Тексты бренда</div><div class="agent-cmd">/hairlove-texts</div><div class="agent-desc">Instagram, сайт, реклама, email</div><span class="badge badge-active">● Активен</span></div>
  </div>
  <div class="node node-insta" data-id="insta">
    <div class="card"><span class="icon">📸</span><div class="agent-name">Instagram</div><div class="agent-cmd">/hairlove-insta</div><div class="agent-desc">Публикация постов, контент-план</div><span class="badge badge-active">● Активен</span></div>
  </div>
  <div class="node node-strategy" data-id="strategy">
    <div class="card"><span class="icon">🎯</span><div class="agent-name">Стратегия</div><div class="agent-cmd">/hairlove-strategy</div><div class="agent-desc">Рост, контент-план, позиционирование</div><span class="badge badge-building">◐ Развивается</span></div>
  </div>
  <div class="node node-site" data-id="site">
    <div class="card"><span class="icon">🌐</span><div class="agent-name">Сайт</div><div class="agent-cmd">/hairlove-site</div><div class="agent-desc">Создание, тексты, SEO</div><span class="badge badge-pending">○ Предстоит</span></div>
  </div>
  <div class="node node-competitors" data-id="competitors">
    <div class="card"><span class="icon">🔍</span><div class="agent-name">Конкуренты</div><div class="agent-cmd">/hairlove-competitors</div><div class="agent-desc">Анализ рынка, тренды, идеи</div><span class="badge badge-pending">○ Предстоит</span></div>
  </div>
  <div class="node node-ads" data-id="ads">
    <div class="card"><span class="icon">📣</span><div class="agent-name">Реклама</div><div class="agent-cmd">/hairlove-ads</div><div class="agent-desc">Meta Ads, Google Ads, таргетинг</div><span class="badge badge-pending">○ Предстоит</span></div>
  </div>
  <div class="tooltip" id="tooltip">
    <div class="t-title" id="t-title"></div>
    <div class="t-row"><span class="t-label">Команда</span><span id="t-cmd"></span></div>
    <div class="t-row"><span class="t-label">Статус</span><span id="t-status"></span></div>
    <div class="t-row"><span class="t-label">Вызов</span><span id="t-usage"></span></div>
  </div>
  <div class="detail-panel">
    <div class="hint">Новая сессия → агент → задача</div>
    <div class="hint"><span class="kbd">/hairlove-texts</span><span>Написать текст</span></div>
    <div class="hint"><span class="kbd">/hairlove-insta</span><span>Опубликовать пост</span></div>
    <div class="hint"><span class="kbd">/hairlove-strategy</span><span>Контент-план</span></div>
  </div>
</div>
<script>
function updateClock(){const n=new Date();document.getElementById('clock').textContent=n.toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit',second:'2-digit'});}
setInterval(updateClock,1000);updateClock();
function drawLines(){
  const cv=document.getElementById('canvas'),sv=document.getElementById('lines');
  const cw=cv.offsetWidth,ch=cv.offsetHeight;
  const cx=cw*0.5,cy=ch*0.5;
  const pos={texts:{x:cw*0.22,y:ch*0.22},insta:{x:cw*0.78,y:ch*0.22},strategy:{x:cw*0.14,y:ch*0.50},site:{x:cw*0.86,y:ch*0.50},competitors:{x:cw*0.22,y:ch*0.78},ads:{x:cw*0.78,y:ch*0.78}};
  const active=['texts','insta'];
  sv.innerHTML='';
  Object.entries(pos).forEach(([id,p])=>{
    const l=document.createElementNS('http://www.w3.org/2000/svg','line');
    l.setAttribute('x1',cx);l.setAttribute('y1',cy);l.setAttribute('x2',p.x);l.setAttribute('y2',p.y);
    l.setAttribute('class','line'+(active.includes(id)?' active':''));
    sv.appendChild(l);
  });
}
drawLines();window.addEventListener('resize',drawLines);
const td={texts:{title:'Тексты бренда',cmd:'/hairlove-texts',status:'✅ Активен',usage:'/hairlove-texts Instagram Lamellar Water'},insta:{title:'Instagram постинг',cmd:'/hairlove-insta',status:'✅ Активен',usage:'/hairlove-insta + фото'},strategy:{title:'Стратегия',cmd:'/hairlove-strategy',status:'◐ В разработке',usage:'/hairlove-strategy контент-план май'},site:{title:'Сайт',cmd:'/hairlove-site',status:'○ Не начат',usage:'/hairlove-site старт'},competitors:{title:'Конкуренты',cmd:'/hairlove-competitors',status:'○ Не начат',usage:'/hairlove-competitors @brandname'},ads:{title:'Реклама',cmd:'/hairlove-ads',status:'○ Не запущена',usage:'/hairlove-ads продажи 100$'}};
const tip=document.getElementById('tooltip');
document.querySelectorAll('.node[data-id]').forEach(node=>{
  const d=td[node.dataset.id];
  node.addEventListener('mouseenter',()=>{
    document.getElementById('t-title').textContent=d.title;
    document.getElementById('t-cmd').textContent=d.cmd;
    document.getElementById('t-status').textContent=d.status;
    document.getElementById('t-usage').textContent=d.usage;
    const r=node.getBoundingClientRect(),cr=document.getElementById('canvas').getBoundingClientRect();
    let x=r.left-cr.left+r.width/2-100,y=r.top-cr.top-110;
    if(y<10)y=r.bottom-cr.top+10;
    if(x<10)x=10;if(x+210>cr.width)x=cr.width-215;
    tip.style.left=x+'px';tip.style.top=y+'px';tip.classList.add('show');
  });
  node.addEventListener('mouseleave',()=>tip.classList.remove('show'));
});
</script>
</body>
</html>"""


@app.route("/agents")
def agents_dashboard():
    return _AGENTS_HTML, 200, {"Content-Type": "text/html; charset=utf-8"}


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
