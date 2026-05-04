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
<html lang="ru" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Система агентов — Pavel</title>
<style>
/* ── CSS-переменные тем ── */
:root {
  --bg:#0a0a14; --bg2:rgba(255,255,255,0.02); --border:rgba(255,255,255,0.07);
  --text:#e8e8f0; --text2:#94a3b8; --muted:#6b7280; --muted2:#4b5563;
  --card-bg:rgba(255,255,255,0.04); --card-border:rgba(255,255,255,0.09);
  --card-hover:rgba(167,139,250,0.07); --card-hover-border:rgba(167,139,250,0.35);
  --dir-active-bg:rgba(167,139,250,0.08); --dir-active-border:rgba(167,139,250,0.45);
  --dir-pending-bg:rgba(255,255,255,0.02); --dir-pending-border:rgba(255,255,255,0.1);
  --dir-pending-text:#374151;
  --line-dir:rgba(167,139,250,0.45); --line-agent:rgba(167,139,250,0.18); --line-pending:rgba(255,255,255,0.06);
  --bar-bg:rgba(10,10,20,0.92); --bar-border:rgba(255,255,255,0.08);
  --kbd-bg:rgba(255,255,255,0.07); --kbd-border:rgba(255,255,255,0.12);
  --ring:rgba(99,102,241,0.15);
  --pavel-bg1:#1e1b4b; --pavel-bg2:#312e81; --pavel-border:#6366f1; --pavel-glow:rgba(99,102,241,0.35);
  --theme-btn-bg:rgba(255,255,255,0.06); --theme-btn-border:rgba(255,255,255,0.12); --theme-btn-active:rgba(167,139,250,0.2);
}
[data-theme="light"] {
  --bg:#f0f0f8; --bg2:rgba(0,0,0,0.02); --border:rgba(0,0,0,0.1);
  --text:#1e1b4b; --text2:#4b5563; --muted:#6b7280; --muted2:#9ca3af;
  --card-bg:rgba(255,255,255,0.85); --card-border:rgba(0,0,0,0.1);
  --card-hover:rgba(99,102,241,0.06); --card-hover-border:rgba(99,102,241,0.4);
  --dir-active-bg:rgba(99,102,241,0.08); --dir-active-border:rgba(99,102,241,0.4);
  --dir-pending-bg:rgba(0,0,0,0.03); --dir-pending-border:rgba(0,0,0,0.12);
  --dir-pending-text:#9ca3af;
  --line-dir:rgba(99,102,241,0.5); --line-agent:rgba(99,102,241,0.2); --line-pending:rgba(0,0,0,0.08);
  --bar-bg:rgba(240,240,248,0.95); --bar-border:rgba(0,0,0,0.1);
  --kbd-bg:rgba(0,0,0,0.05); --kbd-border:rgba(0,0,0,0.12);
  --ring:rgba(99,102,241,0.12);
  --pavel-bg1:#e0e7ff; --pavel-bg2:#c7d2fe; --pavel-border:#6366f1; --pavel-glow:rgba(99,102,241,0.2);
  --theme-btn-bg:rgba(0,0,0,0.05); --theme-btn-border:rgba(0,0,0,0.12); --theme-btn-active:rgba(99,102,241,0.15);
}
* { margin:0; padding:0; box-sizing:border-box; }
body { background:var(--bg); color:var(--text); font-family:-apple-system,'Segoe UI',sans-serif; height:100vh; overflow:hidden; transition:background 0.3s,color 0.3s; }
.header { display:flex; align-items:center; justify-content:space-between; padding:12px 22px; border-bottom:1px solid var(--border); background:var(--bg2); gap:12px; }
.header-brand { font-size:14px; font-weight:600; display:flex; align-items:center; gap:8px; white-space:nowrap; }
.dot { width:7px; height:7px; background:#a78bfa; border-radius:50%; box-shadow:0 0 6px #a78bfa; animation:pulse 2s infinite; flex-shrink:0; }
.header-sub { font-size:11px; color:var(--muted2); flex:1; text-align:center; }
.header-right { display:flex; align-items:center; gap:10px; }
/* Переключатель темы */
.theme-switcher { display:flex; background:var(--theme-btn-bg); border:1px solid var(--theme-btn-border); border-radius:20px; padding:2px; gap:2px; }
.theme-btn { padding:4px 10px; border-radius:16px; font-size:10px; cursor:pointer; border:none; background:transparent; color:var(--muted); transition:all 0.2s; white-space:nowrap; }
.theme-btn:hover { color:var(--text); }
.theme-btn.active { background:var(--theme-btn-active); color:var(--text); font-weight:600; }
.header-time { font-size:12px; color:var(--muted); font-variant-numeric:tabular-nums; white-space:nowrap; }
/* Canvas */
.canvas { position:relative; width:100%; height:calc(100vh - 53px); }
svg.lines { position:absolute; inset:0; width:100%; height:100%; pointer-events:none; z-index:1; }
/* Pavel */
.pavel-node { position:absolute; left:50%; top:50%; transform:translate(-50%,-50%); z-index:10; }
.pavel-card { width:130px; background:linear-gradient(135deg,var(--pavel-bg1),var(--pavel-bg2)); border:2px solid var(--pavel-border); border-radius:18px; padding:18px 14px; text-align:center; box-shadow:0 0 40px var(--pavel-glow); transition:background 0.3s,box-shadow 0.3s; }
.pavel-avatar { width:48px; height:48px; background:linear-gradient(135deg,#6366f1,#a78bfa); border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:22px; margin:0 auto 10px; }
.pavel-name { font-size:14px; font-weight:700; color:var(--text); }
.pavel-role { font-size:9px; color:#a5b4fc; margin-top:2px; letter-spacing:1px; text-transform:uppercase; }
.pulse-ring { position:absolute; left:50%; top:50%; transform:translate(-50%,-50%); width:155px; height:155px; border:1px solid var(--ring); border-radius:50%; pointer-events:none; z-index:0; animation:ring-pulse 3s ease-out infinite; }
.pulse-ring:nth-child(2){animation-delay:1s;} .pulse-ring:nth-child(3){animation-delay:2s;}
/* Direction nodes */
.dir-node { position:absolute; transform:translate(-50%,-50%); z-index:10; }
.dir-card { width:158px; border-radius:14px; padding:13px 14px; text-align:center; transition:all 0.2s; }
.dir-card.active { background:var(--dir-active-bg); border:1.5px solid var(--dir-active-border); box-shadow:0 0 24px rgba(167,139,250,0.1); }
.dir-card.pending { background:var(--dir-pending-bg); border:1.5px dashed var(--dir-pending-border); }
.dir-icon { font-size:24px; margin-bottom:6px; }
.dir-name { font-size:13px; font-weight:600; }
.dir-card.active .dir-name { color:#8b5cf6; }
.dir-card.pending .dir-name { color:var(--dir-pending-text); }
.dir-count { font-size:10px; color:var(--muted); margin-top:2px; }
.dir-badge { display:inline-block; margin-top:7px; padding:2px 9px; border-radius:10px; font-size:10px; }
.dir-badge.active { background:rgba(167,139,250,0.15); color:#a78bfa; }
.dir-badge.pending { background:rgba(107,114,128,0.1); color:var(--dir-pending-text); }
/* Agent nodes */
.agent-node { position:absolute; transform:translate(-50%,-50%); z-index:10; }
.agent-card { width:132px; background:var(--card-bg); border:1px solid var(--card-border); border-radius:13px; padding:11px 10px; text-align:center; transition:all 0.2s; cursor:pointer; backdrop-filter:blur(4px); }
.agent-card:hover { background:var(--card-hover); border-color:var(--card-hover-border); transform:scale(1.05); box-shadow:0 0 18px rgba(99,102,241,0.12); }
.agent-icon { font-size:22px; margin-bottom:5px; }
.agent-name { font-size:11px; font-weight:600; color:var(--text); }
.agent-cmd { font-size:9px; color:#6366f1; font-family:monospace; margin-top:3px; }
.agent-badge { display:inline-block; margin-top:5px; padding:2px 6px; border-radius:8px; font-size:9px; font-weight:600; }
.badge-active { background:rgba(16,185,129,0.15); color:#10b981; border:1px solid rgba(16,185,129,0.25); }
.badge-building { background:rgba(245,158,11,0.12); color:#f59e0b; border:1px solid rgba(245,158,11,0.25); }
.badge-pending { background:rgba(107,114,128,0.1); color:var(--muted); border:1px solid rgba(107,114,128,0.15); }
/* Bottom bar */
.bottom-bar { position:absolute; bottom:18px; left:50%; transform:translateX(-50%); background:var(--bar-bg); border:1px solid var(--bar-border); border-radius:12px; padding:10px 18px; font-size:11px; color:var(--muted); display:flex; gap:20px; backdrop-filter:blur(20px); white-space:nowrap; z-index:20; }
.kbd { background:var(--kbd-bg); border:1px solid var(--kbd-border); padding:1px 6px; border-radius:4px; font-size:10px; color:#8b5cf6; font-family:monospace; }
@keyframes dash { to { stroke-dashoffset:-100; } }
@keyframes pulse { 0%,100%{opacity:1}50%{opacity:.4} }
@keyframes ring-pulse { 0%{transform:translate(-50%,-50%)scale(1);opacity:.4}100%{transform:translate(-50%,-50%)scale(2.2);opacity:0} }
</style>
</head>
<body>
<div class="header">
  <div class="header-brand"><div class="dot"></div>Система агентов — Pavel</div>
  <div class="header-sub">Направления бизнеса → Агенты → Команды</div>
  <div class="header-right">
    <div class="theme-switcher">
      <button class="theme-btn" data-t="light" onclick="setTheme('light')">☀️ Светлая</button>
      <button class="theme-btn active" data-t="dark" onclick="setTheme('dark')">🌙 Тёмная</button>
      <button class="theme-btn" data-t="auto" onclick="setTheme('auto')">⚙️ Авто</button>
    </div>
    <div class="header-time" id="clock">--:--:--</div>
  </div>
</div>
<div class="canvas" id="canvas">
  <div class="pulse-ring"></div><div class="pulse-ring"></div><div class="pulse-ring"></div>
  <svg class="lines" id="lines"></svg>

  <!-- Pavel в центре -->
  <div class="pavel-node">
    <div class="pavel-card">
      <div class="pavel-avatar">👤</div>
      <div class="pavel-name">Павел</div>
      <div class="pavel-role">Владелец</div>
    </div>
  </div>

  <!-- Направление 1: HairLove -->
  <div class="dir-node" style="left:22%;top:50%">
    <div class="dir-card active">
      <div class="dir-icon">💇‍♀️</div>
      <div class="dir-name">HairLove</div>
      <div class="dir-count">6 агентов</div>
      <span class="dir-badge active">● Активно</span>
    </div>
  </div>

  <!-- Направление 2: заглушка -->
  <div class="dir-node" style="left:78%;top:30%">
    <div class="dir-card pending">
      <div class="dir-icon" style="opacity:0.25">📦</div>
      <div class="dir-name">Новое направление</div>
      <span class="dir-badge pending">○ Скоро</span>
    </div>
  </div>

  <!-- Направление 3: заглушка -->
  <div class="dir-node" style="left:78%;top:70%">
    <div class="dir-card pending">
      <div class="dir-icon" style="opacity:0.25">📦</div>
      <div class="dir-name">Новое направление</div>
      <span class="dir-badge pending">○ Скоро</span>
    </div>
  </div>

  <!-- Агенты HairLove -->
  <div class="agent-node" style="left:5%;top:17%">
    <div class="agent-card"><div class="agent-icon">✍️</div><div class="agent-name">Тексты бренда</div><div class="agent-cmd">/hairlove-texts</div><span class="agent-badge badge-active">● Активен</span></div>
  </div>
  <div class="agent-node" style="left:5%;top:37%">
    <div class="agent-card"><div class="agent-icon">📸</div><div class="agent-name">Instagram</div><div class="agent-cmd">/hairlove-insta</div><span class="agent-badge badge-active">● Активен</span></div>
  </div>
  <div class="agent-node" style="left:5%;top:57%">
    <div class="agent-card"><div class="agent-icon">🎯</div><div class="agent-name">Стратегия</div><div class="agent-cmd">/hairlove-strategy</div><span class="agent-badge badge-building">◐ В работе</span></div>
  </div>
  <div class="agent-node" style="left:5%;top:77%">
    <div class="agent-card"><div class="agent-icon">🔍</div><div class="agent-name">Конкуренты</div><div class="agent-cmd">/hairlove-competitors</div><span class="agent-badge badge-pending">○ Предстоит</span></div>
  </div>
  <div class="agent-node" style="left:22%;top:83%">
    <div class="agent-card"><div class="agent-icon">📣</div><div class="agent-name">Реклама</div><div class="agent-cmd">/hairlove-ads</div><span class="agent-badge badge-pending">○ Предстоит</span></div>
  </div>
  <div class="agent-node" style="left:22%;top:17%">
    <div class="agent-card"><div class="agent-icon">🌐</div><div class="agent-name">Сайт</div><div class="agent-cmd">/hairlove-site</div><span class="agent-badge badge-pending">○ Предстоит</span></div>
  </div>

  <div class="bottom-bar">
    <span>Направление → Агент → Задача</span>
    <span><span class="kbd">/hairlove-texts</span> Тексты</span>
    <span><span class="kbd">/hairlove-insta</span> Instagram</span>
    <span><span class="kbd">/hairlove-strategy</span> Стратегия</span>
  </div>
</div>
<script>
// ── Тема ──
const DARK_MQ = window.matchMedia('(prefers-color-scheme: dark)');
function applyTheme(t){
  const actual = t==='auto' ? (DARK_MQ.matches?'dark':'light') : t;
  document.documentElement.setAttribute('data-theme', actual);
  document.querySelectorAll('.theme-btn').forEach(b=>b.classList.toggle('active', b.dataset.t===t));
}
function setTheme(t){ localStorage.setItem('theme',t); applyTheme(t); }
DARK_MQ.addEventListener('change', ()=>{ if(localStorage.getItem('theme')==='auto') applyTheme('auto'); });
applyTheme(localStorage.getItem('theme')||'dark');

// ── Часы ──
function updateClock(){const n=new Date();document.getElementById('clock').textContent=n.toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit',second:'2-digit'});}
setInterval(updateClock,1000);updateClock();

// ── Линии ──
function drawLines(){
  const cv=document.getElementById('canvas'),sv=document.getElementById('lines');
  const cw=cv.offsetWidth,ch=cv.offsetHeight;
  const px=cw*0.5,py=ch*0.5;
  sv.innerHTML='';
  function ln(x1,y1,x2,y2,cls){
    const l=document.createElementNS('http://www.w3.org/2000/svg','line');
    l.setAttribute('x1',x1);l.setAttribute('y1',y1);l.setAttribute('x2',x2);l.setAttribute('y2',y2);
    l.setAttribute('class',cls);sv.appendChild(l);
  }
  const isDark=document.documentElement.getAttribute('data-theme')==='dark';
  sv.innerHTML='';
  // Pavel → направления
  ln(px,py, cw*0.22,ch*0.5, 'line-dir');
  ln(px,py, cw*0.78,ch*0.3, 'line-pending');
  ln(px,py, cw*0.78,ch*0.7, 'line-pending');
  // HairLove → агенты
  const hx=cw*0.22,hy=ch*0.5;
  [[0.05,0.17],[0.05,0.37],[0.05,0.57],[0.05,0.77],[0.22,0.83],[0.22,0.17]].forEach(([ax,ay])=>{
    ln(hx,hy,cw*ax,ch*ay,'line-agent');
  });
}
drawLines();
window.addEventListener('resize',drawLines);
// перерисовать линии при смене темы (цвета берутся из CSS, но stroke инлайновый — ок)
new MutationObserver(drawLines).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
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
