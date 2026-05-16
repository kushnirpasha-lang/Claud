#!/usr/bin/env bash
# HAiR LOVE — установка/обновление VPS-native постинга в Instagram.
# Идемпотентен: можно гонять при каждом деплое.
# Запускается на VPS (root, /opt/assistant).
set -euo pipefail

ASSISTANT_DIR=/opt/assistant
CONTENT_DIR=/opt/hairlove-content
CONTENT_BRANCH=claude/hairlove   # КАНОН: контент консолидирован сюда (obshak выведен 2026-05-16)
REPO=kushnirpasha-lang/Claud
ENV_FILE="$ASSISTANT_DIR/.env"

echo "=== HAiR LOVE IG timer install ==="

# 1. Зависимости (requests, python-dotenv уже в requirements ассистента)
"$ASSISTANT_DIR/venv/bin/pip" install -q requests python-dotenv >/dev/null 2>&1 || true

# 2. Клон ветки контента (для очереди/индекса и push-back индекса)
TOKEN="${GH_TOKEN:-}"
if [ -n "$TOKEN" ]; then
  AUTH_URL="https://${TOKEN}@github.com/${REPO}.git"
else
  AUTH_URL="https://github.com/${REPO}.git"
fi
# Миграция веток (2026-05-16): если старый клон НЕ на канон-ветке —
# сносим и клонируем заново. Дёшево: тут только очередь/индекс,
# фото отдаются через raw-URL, не из локального клона.
if [ -d "$CONTENT_DIR/.git" ]; then
  CUR=$(git -C "$CONTENT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
  if [ "$CUR" != "$CONTENT_BRANCH" ]; then
    echo "Старый клон на '$CUR' ≠ '$CONTENT_BRANCH' — пере-клонирую"
    rm -rf "$CONTENT_DIR"
  fi
fi
if [ ! -d "$CONTENT_DIR/.git" ]; then
  echo "Клонирую $CONTENT_BRANCH → $CONTENT_DIR"
  git clone --branch "$CONTENT_BRANCH" --single-branch "$AUTH_URL" "$CONTENT_DIR"
else
  git -C "$CONTENT_DIR" remote set-url origin "$AUTH_URL"
  git -C "$CONTENT_DIR" fetch origin "$CONTENT_BRANCH"
  git -C "$CONTENT_DIR" checkout -B "$CONTENT_BRANCH" FETCH_HEAD
  git -C "$CONTENT_DIR" reset --hard FETCH_HEAD
fi
git -C "$CONTENT_DIR" config user.email "bot@hairlove.studio"
git -C "$CONTENT_DIR" config user.name "HAiR LOVE Bot"

# 3. Systemd unit + timer
install -m 644 "$ASSISTANT_DIR/hairlove-ig-post.service" /etc/systemd/system/hairlove-ig-post.service
install -m 644 "$ASSISTANT_DIR/hairlove-ig-post.timer"   /etc/systemd/system/hairlove-ig-post.timer
chmod +x "$ASSISTANT_DIR/ig_daily_post.py"

systemctl daemon-reload
systemctl enable --now hairlove-ig-post.timer
systemctl list-timers hairlove-ig-post.timer --no-pager || true

echo "=== Таймер установлен. Следующий запуск: 20:00 Europe/Kiev ==="

# 4. Разовый force-флаг: следующий запуск таймера (сегодня 20:00 Kyiv)
#    опубликует пост, минуя проверку «уже постили сегодня».
#    Нужно потому, что верификационный пост #6 уже вышел сегодня в 16:05
#    и обычная защита от дублей заблокировала бы запуск в 20:00.
#    Флаг одноразовый — скрипт удаляет его при срабатывании.
#    FORCE_NEXT_RUN=0 в env отключает (по умолчанию ставим).
if [ "${FORCE_NEXT_RUN:-1}" = "1" ]; then
  touch "$ASSISTANT_DIR/ig_force_once.flag"
  echo "FORCE-флаг поставлен — таймер в 20:00 опубликует следующий пост"
fi

# 4a. Тест-пинг в Telegram — подтвердить что уведомления живые.
set -a; . "$ENV_FILE"; set +a
CHAT="${TELEGRAM_CHAT_ID:-@Pavel_Kus}"
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  --data-urlencode "chat_id=$CHAT" \
  --data-urlencode "text=✅ HAiR LOVE — деплой ок. Таймер 20:00 Kyiv активен. Telegram працює. Сьогодні о 20:00 вийде наступний пост — прийде підтвердження з назвою файлу, номером і часом." \
  > /dev/null || true

echo "=== Готово. Пост выйдет сегодня в 20:00 Europe/Kiev через таймер ==="
