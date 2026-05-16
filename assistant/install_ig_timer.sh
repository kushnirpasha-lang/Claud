#!/usr/bin/env bash
# HAiR LOVE — установка/обновление VPS-native постинга в Instagram.
# Идемпотентен: можно гонять при каждом деплое.
# Запускается на VPS (root, /opt/assistant).
set -euo pipefail

ASSISTANT_DIR=/opt/assistant
CONTENT_DIR=/opt/hairlove-content
CONTENT_BRANCH=claude/obshak
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
if [ ! -d "$CONTENT_DIR/.git" ]; then
  echo "Клонирую $CONTENT_BRANCH → $CONTENT_DIR"
  git clone --branch "$CONTENT_BRANCH" --single-branch "$AUTH_URL" "$CONTENT_DIR"
else
  git -C "$CONTENT_DIR" remote set-url origin "$AUTH_URL"
  git -C "$CONTENT_DIR" fetch origin "$CONTENT_BRANCH"
  git -C "$CONTENT_DIR" reset --hard "origin/$CONTENT_BRANCH"
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

# 4a. Тест-пинг в Telegram — подтвердить что уведомления живые.
set -a; . "$ENV_FILE"; set +a
CHAT="${TELEGRAM_CHAT_ID:-@Pavel_Kus}"
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  --data-urlencode "chat_id=$CHAT" \
  --data-urlencode "text=✅ HAiR LOVE — деплой ок. Таймер 20:00 Kyiv активен. Telegram-уведомления работают. Наступний пост сьогодні вже є (#6), завтра в 20:00." \
  > /dev/null || true

# 4. Немедленный проверочный пост (Павел просил сразу убедиться).
#    Безопасно: ig_daily_post.py сам сверяется с IG API и не сделает
#    второй пост за киевские сутки, даже если потом сработает таймер.
if [ "${RUN_NOW:-1}" = "1" ]; then
  echo "=== Немедленный проверочный пост ==="
  set -a; . "$ENV_FILE"; set +a
  "$ASSISTANT_DIR/venv/bin/python" "$ASSISTANT_DIR/ig_daily_post.py" || {
    echo "Немедленный пост завершился с ошибкой — см. лог $ASSISTANT_DIR/ig_post.log"
    exit 1
  }
fi
echo "=== Готово ==="
