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
<!-- updated: 04.05.2026 21:00 -->
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Система агентов — Pavel</title>
<style>
:root {
  --bg:#07071a; --bg2:rgba(255,255,255,0.02); --border:rgba(255,255,255,0.07);
  --text:#e8e8f0; --text2:#94a3b8; --muted:#6b7280; --muted2:#4b5563;
  --card-bg:rgba(255,255,255,0.04); --card-border:rgba(255,255,255,0.09);
  --card-hover:rgba(167,139,250,0.08); --card-hover-border:rgba(167,139,250,0.4);
  --card-selected:rgba(167,139,250,0.13); --card-selected-border:rgba(167,139,250,0.65);
  --dir-pending-bg:rgba(255,255,255,0.02); --dir-pending-border:rgba(255,255,255,0.1); --dir-pending-text:#374151;
  --bar-bg:rgba(7,7,26,0.92); --bar-border:rgba(255,255,255,0.08);
  --kbd-bg:rgba(255,255,255,0.07); --kbd-border:rgba(255,255,255,0.12);
  --ring:rgba(139,92,246,0.12);
  --pavel-bg1:#1e1b4b; --pavel-bg2:#312e81; --pavel-border:#6366f1; --pavel-glow:rgba(99,102,241,0.4);
  --hl-bg1:#1a0a2e; --hl-bg2:#2d1a4a; --hl-border:#8b5cf6; --hl-glow:rgba(139,92,246,0.5);
  --theme-btn-bg:rgba(255,255,255,0.05); --theme-btn-border:rgba(255,255,255,0.1); --theme-btn-active:rgba(167,139,250,0.18);
  --panel-bg:#0c0c22; --panel-border:rgba(139,92,246,0.2); --panel-shadow:rgba(0,0,0,0.6);
  --section-done:#10b981; --section-progress:#f59e0b; --section-next:#6366f1;
}
[data-theme="light"] {
  --bg:#eeeef8; --bg2:rgba(0,0,0,0.02); --border:rgba(0,0,0,0.09);
  --text:#1e1b4b; --text2:#4b5563; --muted:#6b7280; --muted2:#9ca3af;
  --card-bg:rgba(255,255,255,0.9); --card-border:rgba(0,0,0,0.1);
  --card-hover:rgba(99,102,241,0.07); --card-hover-border:rgba(99,102,241,0.4);
  --card-selected:rgba(99,102,241,0.1); --card-selected-border:rgba(99,102,241,0.6);
  --dir-pending-bg:rgba(0,0,0,0.03); --dir-pending-border:rgba(0,0,0,0.1); --dir-pending-text:#9ca3af;
  --bar-bg:rgba(238,238,248,0.95); --bar-border:rgba(0,0,0,0.1);
  --kbd-bg:rgba(0,0,0,0.05); --kbd-border:rgba(0,0,0,0.1);
  --ring:rgba(99,102,241,0.1);
  --pavel-bg1:#e0e7ff; --pavel-bg2:#c7d2fe; --pavel-border:#6366f1; --pavel-glow:rgba(99,102,241,0.2);
  --hl-bg1:#f3e8ff; --hl-bg2:#e9d5ff; --hl-border:#8b5cf6; --hl-glow:rgba(139,92,246,0.2);
  --theme-btn-bg:rgba(0,0,0,0.04); --theme-btn-border:rgba(0,0,0,0.1); --theme-btn-active:rgba(99,102,241,0.12);
  --panel-bg:#ffffff; --panel-border:rgba(99,102,241,0.2); --panel-shadow:rgba(0,0,0,0.12);
}
* { margin:0; padding:0; box-sizing:border-box; }
body { background:var(--bg); color:var(--text); font-family:-apple-system,'Segoe UI',sans-serif; height:100vh; overflow:hidden; transition:background 0.3s,color 0.3s; }
/* Header */
.header { display:flex; align-items:center; justify-content:space-between; padding:11px 22px; border-bottom:1px solid var(--border); background:var(--bg2); gap:12px; }
.header-brand { font-size:14px; font-weight:600; display:flex; align-items:center; gap:8px; white-space:nowrap; }
.dot { width:7px; height:7px; background:#a78bfa; border-radius:50%; box-shadow:0 0 6px #a78bfa; animation:blink 2s infinite; flex-shrink:0; }
.header-sub { font-size:11px; color:var(--muted2); flex:1; text-align:center; }
.header-right { display:flex; align-items:center; gap:10px; }
.theme-switcher { display:flex; background:var(--theme-btn-bg); border:1px solid var(--theme-btn-border); border-radius:20px; padding:2px; gap:2px; }
.theme-btn { padding:4px 9px; border-radius:16px; font-size:10px; cursor:pointer; border:none; background:transparent; color:var(--muted); transition:all 0.2s; white-space:nowrap; }
.theme-btn:hover { color:var(--text); }
.theme-btn.active { background:var(--theme-btn-active); color:var(--text); font-weight:600; }
.header-time { font-size:12px; color:var(--muted); font-variant-numeric:tabular-nums; white-space:nowrap; }
/* Canvas */
.canvas { position:relative; width:100%; height:calc(100vh - 52px); overflow:hidden; }
svg.lines { position:absolute; inset:0; width:100%; height:100%; pointer-events:none; z-index:1; }
/* Pavel */
.pavel-node { position:absolute; left:64%; top:50%; transform:translate(-50%,-50%); z-index:10; }
.pavel-card { width:126px; background:linear-gradient(135deg,var(--pavel-bg1),var(--pavel-bg2)); border:2px solid var(--pavel-border); border-radius:18px; padding:16px 12px; text-align:center; box-shadow:0 0 40px var(--pavel-glow); }
.pavel-avatar { width:44px; height:44px; background:linear-gradient(135deg,#6366f1,#a78bfa); border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:20px; margin:0 auto 9px; }
.pavel-name { font-size:13px; font-weight:700; }
.pavel-role { font-size:9px; color:#a5b4fc; margin-top:2px; letter-spacing:1px; text-transform:uppercase; }
/* HairLove star */
.hl-node { position:absolute; left:20%; top:50%; transform:translate(-50%,-50%); z-index:10; }
.hl-card { width:136px; background:linear-gradient(135deg,var(--hl-bg1),var(--hl-bg2)); border:2px solid var(--hl-border); border-radius:18px; padding:15px 12px; text-align:center; box-shadow:0 0 50px var(--hl-glow), 0 0 20px var(--hl-glow); }
.hl-icon { font-size:28px; margin-bottom:7px; }
.hl-name { font-size:14px; font-weight:700; color:#c4b5fd; }
.hl-sub { font-size:9px; color:#7c3aed; margin-top:2px; text-transform:uppercase; letter-spacing:1px; }
.hl-badge { display:inline-block; margin-top:8px; padding:2px 10px; border-radius:10px; font-size:9px; background:rgba(139,92,246,0.2); color:#c4b5fd; border:1px solid rgba(139,92,246,0.3); }
/* Pulse rings around HairLove */
.hl-ring { position:absolute; left:20%; top:50%; border-radius:50%; pointer-events:none; z-index:0; animation:ring-exp 4s ease-out infinite; border:1px solid rgba(139,92,246,0.15); }
.hl-ring:nth-child(1) { width:180px; height:180px; margin-left:-90px; margin-top:-90px; animation-delay:0s; }
.hl-ring:nth-child(2) { width:180px; height:180px; margin-left:-90px; margin-top:-90px; animation-delay:1.3s; }
.hl-ring:nth-child(3) { width:180px; height:180px; margin-left:-90px; margin-top:-90px; animation-delay:2.6s; }
/* Placeholder directions */
.dir-node { position:absolute; transform:translate(-50%,-50%); z-index:5; }
.dir-card { width:140px; border-radius:13px; padding:12px; text-align:center; background:var(--dir-pending-bg); border:1.5px dashed var(--dir-pending-border); }
.dir-icon { font-size:22px; margin-bottom:5px; opacity:0.22; }
.dir-name { font-size:11px; font-weight:600; color:var(--dir-pending-text); }
.dir-badge { display:inline-block; margin-top:6px; padding:2px 8px; border-radius:8px; font-size:9px; background:rgba(107,114,128,0.08); color:var(--dir-pending-text); }
/* Planet (agent) nodes */
.planet-node { position:absolute; transform:translate(-50%,-50%); z-index:10; }
.planet-card { width:124px; background:var(--card-bg); border:1px solid var(--card-border); border-radius:14px; padding:10px 9px; text-align:center; cursor:pointer; backdrop-filter:blur(6px); transition:all 0.2s; }
.planet-card:hover { background:var(--card-hover); border-color:var(--card-hover-border); transform:scale(1.06); box-shadow:0 0 22px rgba(139,92,246,0.15); }
.planet-card.selected { background:var(--card-selected); border-color:var(--card-selected-border); box-shadow:0 0 26px rgba(139,92,246,0.25); }
.agent-icon { font-size:20px; margin-bottom:4px; }
.agent-name { font-size:10.5px; font-weight:600; color:var(--text); }
.agent-cmd { font-size:9px; color:#7c3aed; font-family:monospace; margin-top:3px; display:inline-block; padding:2px 5px; border-radius:5px; border:1px solid transparent; transition:all 0.15s; }
.agent-cmd:hover { background:rgba(124,58,237,0.15); border-color:rgba(124,58,237,0.4); color:#a78bfa; cursor:copy; }
.agent-cmd.copied { background:rgba(16,185,129,0.15); border-color:rgba(16,185,129,0.4); color:#10b981; }
.agent-focus { font-size:8.5px; color:var(--muted); margin-top:4px; line-height:1.3; font-style:italic; }
.agent-updated { font-size:8px; color:var(--muted2); margin-top:3px; }
.agent-badge { display:inline-block; margin-top:5px; padding:2px 6px; border-radius:7px; font-size:8.5px; font-weight:600; }
.badge-active { background:rgba(16,185,129,0.14); color:#10b981; border:1px solid rgba(16,185,129,0.22); }
.badge-building { background:rgba(245,158,11,0.11); color:#f59e0b; border:1px solid rgba(245,158,11,0.22); }
.badge-pending { background:rgba(107,114,128,0.09); color:var(--muted); border:1px solid rgba(107,114,128,0.14); }
/* Toast */
.copy-toast { position:fixed; bottom:68px; left:50%; transform:translateX(-50%) translateY(10px); background:#1e1b4b; border:1px solid rgba(99,102,241,0.4); color:#a5b4fc; font-size:12px; padding:8px 18px; border-radius:10px; opacity:0; transition:all 0.25s; pointer-events:none; z-index:200; white-space:nowrap; box-shadow:0 4px 20px rgba(0,0,0,0.4); }
.copy-toast.show { opacity:1; transform:translateX(-50%) translateY(0); }
/* Connection legend */
.legend { position:absolute; bottom:18px; left:18px; background:var(--bar-bg); border:1px solid var(--bar-border); border-radius:10px; padding:8px 14px; font-size:10px; color:var(--muted); display:flex; flex-direction:column; gap:5px; backdrop-filter:blur(16px); z-index:20; }
.legend-row { display:flex; align-items:center; gap:7px; }
.legend-line { width:28px; height:2px; border-radius:1px; flex-shrink:0; }
.ll-content { background:rgba(99,102,241,0.7); }
.ll-data { background:rgba(245,158,11,0.75); }
.ll-launch { background:rgba(244,63,94,0.75); }
/* Bottom hints */
.bottom-bar { position:absolute; bottom:18px; left:50%; transform:translateX(-50%); background:var(--bar-bg); border:1px solid var(--bar-border); border-radius:12px; padding:9px 16px; font-size:11px; color:var(--muted); display:flex; gap:18px; backdrop-filter:blur(20px); white-space:nowrap; z-index:20; }
.kbd { background:var(--kbd-bg); border:1px solid var(--kbd-border); padding:1px 5px; border-radius:4px; font-size:9px; color:#8b5cf6; font-family:monospace; }
/* SVG connection classes */
.orbit-ring { fill:none; stroke:rgba(139,92,246,0.1); stroke-width:1; stroke-dasharray:5 8; }
.conn-spoke { stroke:rgba(139,92,246,0.07); stroke-width:1; fill:none; }
.conn-main { stroke:rgba(139,92,246,0.45); stroke-width:1.5; stroke-dasharray:6 4; fill:none; animation:flow 3s linear infinite; }
.conn-pending { stroke:rgba(255,255,255,0.05); stroke-width:1; stroke-dasharray:3 6; fill:none; }
.conn-content { stroke:rgba(99,102,241,0.6); stroke-width:1.5; stroke-dasharray:5 4; fill:none; animation:flow 3.2s linear infinite; }
.conn-data { stroke:rgba(245,158,11,0.65); stroke-width:1.5; stroke-dasharray:4 4; fill:none; animation:flow 2.5s linear infinite; }
.conn-launch { stroke:rgba(244,63,94,0.7); stroke-width:2; stroke-dasharray:7 4; fill:none; animation:flow 1.8s linear infinite; }
/* Detail panel */
.detail-panel { position:fixed; top:52px; right:0; bottom:0; width:360px; background:var(--panel-bg); border-left:1px solid var(--panel-border); box-shadow:-8px 0 32px var(--panel-shadow); z-index:100; overflow-y:auto; transform:translateX(100%); transition:transform 0.3s cubic-bezier(0.4,0,0.2,1); display:flex; flex-direction:column; }
.detail-panel.open { transform:translateX(0); }
.panel-header { padding:17px 20px 13px; border-bottom:1px solid var(--border); display:flex; align-items:flex-start; justify-content:space-between; gap:12px; position:sticky; top:0; background:var(--panel-bg); z-index:1; }
.panel-header-left { display:flex; align-items:center; gap:10px; }
.panel-agent-icon { font-size:28px; }
.panel-agent-name { font-size:15px; font-weight:700; color:var(--text); }
.panel-agent-cmd { font-size:10px; color:#7c3aed; font-family:monospace; margin-top:2px; }
.panel-close { width:28px; height:28px; border-radius:8px; background:var(--card-bg); border:1px solid var(--card-border); cursor:pointer; display:flex; align-items:center; justify-content:center; font-size:14px; color:var(--muted); transition:all 0.15s; flex-shrink:0; }
.panel-close:hover { background:var(--card-hover); color:var(--text); }
.panel-updated { padding:9px 20px; font-size:11px; color:var(--muted); border-bottom:1px solid var(--border); display:flex; align-items:center; gap:6px; }
.panel-upd-dot { width:6px; height:6px; border-radius:50%; background:#8b5cf6; flex-shrink:0; }
.panel-body { padding:15px 20px; display:flex; flex-direction:column; gap:15px; }
.panel-section-title { font-size:10px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; margin-bottom:9px; display:flex; align-items:center; gap:7px; }
.panel-items { display:flex; flex-direction:column; gap:5px; }
.panel-item { font-size:12px; color:var(--text2); line-height:1.45; padding:7px 10px; border-radius:8px; background:var(--card-bg); border-left:2px solid transparent; display:flex; align-items:flex-start; gap:8px; }
.section-done .panel-section-title { color:var(--section-done); }
.section-done .panel-item { border-left-color:var(--section-done); }
.section-progress .panel-section-title { color:var(--section-progress); }
.section-progress .panel-item { border-left-color:var(--section-progress); }
.section-next .panel-section-title { color:var(--section-next); }
.section-next .panel-item { border-left-color:var(--section-next); }
.item-bullet { flex-shrink:0; font-size:11px; margin-top:1px; }
.panel-empty { font-size:11px; color:var(--muted2); font-style:italic; padding:5px 0; }
/* Animations */
@keyframes flow { to { stroke-dashoffset:-100; } }
@keyframes blink { 0%,100%{opacity:1}50%{opacity:.35} }
@keyframes ring-exp { 0%{transform:scale(1);opacity:.5}100%{transform:scale(3.2);opacity:0} }
</style>
</head>
<body>
<div class="header">
  <div class="header-brand"><div class="dot"></div>Система агентов — Pavel</div>
  <div class="header-sub">Галактика HairLove — Агенты — Связи</div>
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
  <svg class="lines" id="lines"></svg>

  <!-- Pulse rings HairLove -->
  <div class="hl-ring"></div>
  <div class="hl-ring"></div>
  <div class="hl-ring"></div>

  <!-- Pavel -->
  <div class="pavel-node">
    <div class="pavel-card">
      <div class="pavel-avatar">👤</div>
      <div class="pavel-name">Павел</div>
      <div class="pavel-role">Владелец</div>
    </div>
  </div>

  <!-- HairLove звезда -->
  <div class="hl-node">
    <div class="hl-card">
      <div class="hl-icon">💇‍♀️</div>
      <div class="hl-name">HairLove</div>
      <div class="hl-sub">Галактика</div>
      <span class="hl-badge">● 6 агентов</span>
    </div>
  </div>

  <!-- Placeholder directions справа от Павла -->
  <div class="dir-node" style="left:82%;top:28%">
    <div class="dir-card">
      <div class="dir-icon">📦</div>
      <div class="dir-name">Новое направление</div>
      <span class="dir-badge">○ Скоро</span>
    </div>
  </div>
  <div class="dir-node" style="left:82%;top:72%">
    <div class="dir-card">
      <div class="dir-icon">📦</div>
      <div class="dir-name">Новое направление</div>
      <span class="dir-badge">○ Скоро</span>
    </div>
  </div>

  <!-- ── Планеты-агенты (орбита вокруг HairLove) ── -->

  <!-- Стратегия: верх (12 часов) -->
  <div class="planet-node" style="left:20%;top:11%">
    <div class="planet-card" id="card-strategy" onclick="openPanel('strategy',event)">
      <div class="agent-icon">🎯</div>
      <div class="agent-name">Стратегия</div>
      <div class="agent-cmd" title="Скопировать" onclick="copyCmd(this,'/hairlove-strategy',event)">/hairlove-strategy</div>
      <div class="agent-focus">Центр сети, дорожная карта</div>
      <div class="agent-updated" id="upd-strategy">—</div>
      <span class="agent-badge badge-building">◐ В работе</span>
    </div>
  </div>

  <!-- Тексты: верхний левый (10 часов) -->
  <div class="planet-node" style="left:5%;top:30%">
    <div class="planet-card" id="card-texts" onclick="openPanel('texts',event)">
      <div class="agent-icon">✍️</div>
      <div class="agent-name">Тексты бренда</div>
      <div class="agent-cmd" title="Скопировать" onclick="copyCmd(this,'/hairlove-texts',event)">/hairlove-texts</div>
      <div class="agent-focus">Контент для всех каналов</div>
      <div class="agent-updated" id="upd-texts">—</div>
      <span class="agent-badge badge-active">● Активен</span>
    </div>
  </div>

  <!-- Конкуренты: нижний левый (8 часов) -->
  <div class="planet-node" style="left:5%;top:70%">
    <div class="planet-card" id="card-competitors" onclick="openPanel('competitors',event)">
      <div class="agent-icon">🔍</div>
      <div class="agent-name">Конкуренты</div>
      <div class="agent-cmd" title="Скопировать" onclick="copyCmd(this,'/hairlove-competitors',event)">/hairlove-competitors</div>
      <div class="agent-focus">Данные для стратегии и рекламы</div>
      <div class="agent-updated" id="upd-competitors">—</div>
      <span class="agent-badge badge-pending">○ Ждёт задачи</span>
    </div>
  </div>

  <!-- Instagram: низ (6 часов) -->
  <div class="planet-node" style="left:20%;top:89%">
    <div class="planet-card" id="card-insta" onclick="openPanel('insta',event)">
      <div class="agent-icon">📸</div>
      <div class="agent-name">Instagram</div>
      <div class="agent-cmd" title="Скопировать" onclick="copyCmd(this,'/hairlove-insta',event)">/hairlove-insta</div>
      <div class="agent-focus">Публикация постов</div>
      <div class="agent-updated" id="upd-insta">—</div>
      <span class="agent-badge badge-active">● Активен</span>
    </div>
  </div>

  <!-- Сайт: верхний правый (2 часа) -->
  <div class="planet-node" style="left:35%;top:30%">
    <div class="planet-card" id="card-site" onclick="openPanel('site',event)">
      <div class="agent-icon">🌐</div>
      <div class="agent-name">Сайт</div>
      <div class="agent-cmd" title="Скопировать" onclick="copyCmd(this,'/hairlove-site',event)">/hairlove-site</div>
      <div class="agent-focus">B2B витрина, следующий приоритет</div>
      <div class="agent-updated" id="upd-site">—</div>
      <span class="agent-badge badge-pending">○ Следующий</span>
    </div>
  </div>

  <!-- Реклама: нижний правый (4 часа) -->
  <div class="planet-node" style="left:35%;top:70%">
    <div class="planet-card" id="card-ads" onclick="openPanel('ads',event)">
      <div class="agent-icon">📣</div>
      <div class="agent-name">Реклама</div>
      <div class="agent-cmd" title="Скопировать" onclick="copyCmd(this,'/hairlove-ads',event)">/hairlove-ads</div>
      <div class="agent-focus">Meta Ads, стреляет в сайт и Insta</div>
      <div class="agent-updated" id="upd-ads">—</div>
      <span class="agent-badge badge-pending">○ Этап 2</span>
    </div>
  </div>

  <!-- Легенда связей -->
  <div class="legend">
    <div class="legend-row"><div class="legend-line ll-content"></div><span>Тексты → канал</span></div>
    <div class="legend-row"><div class="legend-line ll-data"></div><span>Конкуренты → анализ</span></div>
    <div class="legend-row"><div class="legend-line ll-launch"></div><span>Реклама → запуск</span></div>
  </div>

  <div class="bottom-bar">
    <span>Нажми на планету → детали</span>
    <span><span class="kbd">/hairlove-strategy</span> Стратегия</span>
    <span><span class="kbd">/hairlove-texts</span> Тексты</span>
    <span><span class="kbd">/hairlove-ads</span> Реклама</span>
  </div>
</div>

<!-- Toast -->
<div class="copy-toast" id="copy-toast">📋 Скопировано</div>

<!-- Detail panel -->
<div class="detail-panel" id="detail-panel">
  <div class="panel-header">
    <div class="panel-header-left">
      <div class="panel-agent-icon" id="panel-icon">🤖</div>
      <div>
        <div class="panel-agent-name" id="panel-name">Агент</div>
        <div class="panel-agent-cmd" id="panel-cmd">/command</div>
      </div>
    </div>
    <div class="panel-close" onclick="closePanel()">✕</div>
  </div>
  <div class="panel-updated"><div class="panel-upd-dot"></div><span id="panel-updated-text">Обновлён —</span></div>
  <div class="panel-body">
    <div class="panel-section section-done">
      <div class="panel-section-title">✅ Сделано</div>
      <div class="panel-items" id="items-done"></div>
    </div>
    <div class="panel-section section-progress">
      <div class="panel-section-title">🔄 В работе</div>
      <div class="panel-items" id="items-progress"></div>
    </div>
    <div class="panel-section section-next">
      <div class="panel-section-title">⏭️ Следующий шаг</div>
      <div class="panel-items" id="items-next"></div>
    </div>
  </div>
</div>

<script>
// ── Данные агентов ──
const AGENTS = {
  strategy: {
    icon:'🎯', name:'Стратегия', cmd:'/hairlove-strategy',
    updated:'04.05.2026 в 21:00',
    done:['Анализ конкурентов: deeply, jNOWA, SEKTA, K18, Olaplex','Таблица цен: 9 SKU, 4 уровня (дистр/салон/РРЦ мастер/РРЦ интернет)','Структура сайта: 5 страниц, B2B витрина','Instagram: 6 рубрик с частотой и форматами','Дорожная карта: 3 этапа, роли Павел/Максим','Продажи: крем-спрей ~3500-4000 шт., термозащита 2-я партия'],
    progress:['Сайт — следующий приоритет, Tilda vs Shopify','Прямой B2B Одесса — стартует Максим'],
    next:['Решить: Tilda или Shopify','Данные по продажам Ламелярной маски','Список активных дистрибуторов для ABC-анализа'],
  },
  texts: {
    icon:'✍️', name:'Тексты бренда', cmd:'/hairlove-texts',
    updated:'04.05.2026 в 21:00',
    done:['База знаний: составы, pH, объёмы всех продуктов','Голос бренда: живой, тёплый, экспертный','Список запрещённых слов и шаблонов','Форматы: Instagram, сайт, реклама, email'],
    progress:['Первые посты для Instagram — в очереди'],
    next:['Пост: представление термозащиты (2-я партия)','Карточки продуктов для сайта (4 шт.)','Текст раздела "О бренде": Made in Italy, история'],
  },
  competitors: {
    icon:'🔍', name:'Конкуренты', cmd:'/hairlove-competitors',
    updated:'04.05.2026 в 21:00',
    done:['deeply.com.ua: минимализм, простые составы','jnowaprofessional.ua: B2B, обучение','hairsekta.com: Pro-программа (идея HairLove Pro)','K18hair.com и Olaplex.com — международные ориентиры'],
    progress:[],
    next:['Ценовые стратегии конкурентов (акции, скидки)','Мониторинг Instagram — что работает у них','Новые игроки на рынке Украины'],
  },
  insta: {
    icon:'📸', name:'Instagram', cmd:'/hairlove-insta',
    updated:'04.05.2026 в 14:20',
    done:['Токен настроен, публикация работает','Workflow ig-publish.yml через GitHub Actions','Превью-страница перед постингом','Последний пост: ID 17926264809292098'],
    progress:['Контент-план есть, посты не запущены','Токен обновлять каждые ~60 дней'],
    next:['Пост: термозащита (2-я партия — повод)','Пост: Made in Italy — что это значит','Reels: применение крем-спрея'],
  },
  site: {
    icon:'🌐', name:'Сайт', cmd:'/hairlove-site',
    updated:'04.05.2026 в 21:00',
    done:['Структура: 5 страниц в стратегии','Дизайн-требования: цвет, шрифт, mobile-first','Tilda (витрина) vs Shopify (магазин) — сравнение'],
    progress:['Решение о платформе ждёт Павла'],
    next:['Выбрать: Tilda или Shopify','Главная: Hero + 4 продукта + УТП + CTA','B2B страница: условия + прайс + форма'],
  },
  ads: {
    icon:'📣', name:'Реклама', cmd:'/hairlove-ads',
    updated:'03.05.2026 в 12:00',
    done:[],
    progress:[],
    next:['Этап 2 — после создания сайта','Подобрать подрядчика по Meta Ads','Подготовить креативы (фото + тексты)','Настроить пиксель Facebook на сайте'],
  },
};

Object.entries(AGENTS).forEach(([id,a]) => {
  const el = document.getElementById('upd-'+id);
  if(el) el.textContent = 'обновлён '+a.updated;
});

// ── Копирование ──
let toastTimer = null;
function copyCmd(el, cmd, event) {
  event.stopPropagation();
  navigator.clipboard.writeText(cmd).then(() => {
    el.classList.add('copied');
    const t = document.getElementById('copy-toast');
    t.textContent = '📋 '+cmd+' — скопировано!';
    t.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { t.classList.remove('show'); el.classList.remove('copied'); }, 2000);
  });
}

// ── Панель ──
let currentAgent = null;
function openPanel(id, event) {
  const a = AGENTS[id]; if(!a) return;
  currentAgent = id;
  document.querySelectorAll('.planet-card').forEach(c=>c.classList.remove('selected'));
  document.getElementById('card-'+id).classList.add('selected');
  document.getElementById('panel-icon').textContent = a.icon;
  document.getElementById('panel-name').textContent = a.name;
  document.getElementById('panel-cmd').textContent = a.cmd;
  document.getElementById('panel-updated-text').textContent = 'Обновлён '+a.updated;
  renderItems('items-done', a.done, '✓');
  renderItems('items-progress', a.progress, '◐');
  renderItems('items-next', a.next, '→');
  document.getElementById('detail-panel').classList.add('open');
}
function renderItems(cid, items, bullet) {
  const el = document.getElementById(cid);
  if(!items||items.length===0){ el.innerHTML='<div class="panel-empty">Пусто</div>'; return; }
  el.innerHTML = items.map(t=>`<div class="panel-item"><span class="item-bullet">${bullet}</span><span>${t}</span></div>`).join('');
}
function closePanel() {
  document.getElementById('detail-panel').classList.remove('open');
  document.querySelectorAll('.planet-card').forEach(c=>c.classList.remove('selected'));
  currentAgent = null;
}
document.addEventListener('keydown', e=>{ if(e.key==='Escape') closePanel(); });

// ── Тема ──
const DARK_MQ = window.matchMedia('(prefers-color-scheme: dark)');
function applyTheme(t){ const a=t==='auto'?(DARK_MQ.matches?'dark':'light'):t; document.documentElement.setAttribute('data-theme',a); document.querySelectorAll('.theme-btn').forEach(b=>b.classList.toggle('active',b.dataset.t===t)); }
function setTheme(t){ localStorage.setItem('theme',t); applyTheme(t); }
DARK_MQ.addEventListener('change',()=>{ if(localStorage.getItem('theme')==='auto') applyTheme('auto'); });
applyTheme(localStorage.getItem('theme')||'dark');

// ── Часы ──
function updateClock(){ const n=new Date(); document.getElementById('clock').textContent=n.toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit',second:'2-digit'}); }
setInterval(updateClock,1000); updateClock();

// ── Рисование: орбита + связи ──
function drawAll() {
  const cv = document.getElementById('canvas');
  const sv = document.getElementById('lines');
  const cw = cv.offsetWidth, ch = cv.offsetHeight;
  sv.innerHTML = '';

  const P = {
    pavel:       [cw*0.64, ch*0.50],
    hl:          [cw*0.20, ch*0.50],
    strategy:    [cw*0.20, ch*0.11],
    texts:       [cw*0.05, ch*0.30],
    competitors: [cw*0.05, ch*0.70],
    insta:       [cw*0.20, ch*0.89],
    site:        [cw*0.35, ch*0.30],
    ads:         [cw*0.35, ch*0.70],
    dir1:        [cw*0.82, ch*0.28],
    dir2:        [cw*0.82, ch*0.72],
  };

  function mkLine(a, b, cls) {
    const [x1,y1]=P[a],[x2,y2]=P[b];
    const el=document.createElementNS('http://www.w3.org/2000/svg','line');
    el.setAttribute('x1',x1); el.setAttribute('y1',y1);
    el.setAttribute('x2',x2); el.setAttribute('y2',y2);
    el.setAttribute('class',cls); sv.appendChild(el);
  }

  function mkCurve(a, b, cls, bend) {
    const [x1,y1]=P[a],[x2,y2]=P[b];
    const mx=(x1+x2)/2, my=(y1+y2)/2;
    const dx=x2-x1, dy=y2-y1;
    const len=Math.sqrt(dx*dx+dy*dy)||1;
    const cx=mx+(-dy/len)*bend*len;
    const cy=my+(dx/len)*bend*len;
    const el=document.createElementNS('http://www.w3.org/2000/svg','path');
    el.setAttribute('d',`M${x1},${y1} Q${cx},${cy} ${x2},${y2}`);
    el.setAttribute('class',cls); el.setAttribute('fill','none');
    sv.appendChild(el);
  }

  // Орбитальное кольцо HairLove
  const orb = document.createElementNS('http://www.w3.org/2000/svg','ellipse');
  orb.setAttribute('cx', P.hl[0]);
  orb.setAttribute('cy', P.hl[1]);
  orb.setAttribute('rx', cw*0.165);
  orb.setAttribute('ry', ch*0.405);
  orb.setAttribute('class','orbit-ring');
  sv.appendChild(orb);

  // Спицы HairLove → планеты
  ['strategy','texts','competitors','insta','site','ads'].forEach(a=>mkLine('hl',a,'conn-spoke'));

  // Pavel → HairLove
  mkLine('pavel','hl','conn-main');
  // Pavel → направления-заглушки
  mkLine('pavel','dir1','conn-pending');
  mkLine('pavel','dir2','conn-pending');

  // ─── Сетевые связи ───
  // Тексты → каналы (синий)
  mkCurve('texts','site',       'conn-content', 0.16);
  mkCurve('texts','insta',      'conn-content',-0.16);
  mkCurve('texts','ads',        'conn-content', 0.11);
  // Конкуренты → аналитика (янтарный)
  mkCurve('competitors','strategy','conn-data',-0.16);
  mkCurve('competitors','ads',     'conn-data', 0.12);
  // Реклама → запуск (розовый)
  mkCurve('ads','insta','conn-launch', 0.16);
  mkCurve('ads','site', 'conn-launch',-0.14);
}

drawAll();
window.addEventListener('resize', drawAll);
new MutationObserver(drawAll).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
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
