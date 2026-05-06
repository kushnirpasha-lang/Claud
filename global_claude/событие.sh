#!/usr/bin/env bash
# Отправка события в агентный дашборд
# Использование: событие.sh <project> <agent> <type> "<message>" [task_id] [artifact] [hand_off_to]
# Типы: start | step | complete | handoff | error | wait

set -e

PROJECT="${1:-unknown}"
AGENT="${2:-unknown}"
TYPE="${3:-step}"
MSG="${4:-}"
TASK_ID="${5:-}"
ARTIFACT="${6:-}"
HANDOFF="${7:-}"

DASHBOARD_URL="${DASHBOARD_URL:-http://127.0.0.1:8080}"
TOKEN="${DASHBOARD_TOKEN:-}"

JSON=$(cat <<EOF
{
  "ts": "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)",
  "project": "$PROJECT",
  "agent": "$AGENT",
  "type": "$TYPE",
  "message": "$MSG",
  "task_id": "$TASK_ID",
  "artifact": "$ARTIFACT",
  "hand_off_to": "$HANDOFF"
}
EOF
)

# Отправляем в дашборд, не падаем если недоступен
if [ -n "$TOKEN" ]; then
  curl -s -X POST "$DASHBOARD_URL/events" \
    -H "Content-Type: application/json" \
    -H "X-Token: $TOKEN" \
    -d "$JSON" >/dev/null 2>&1 || true
else
  curl -s -X POST "$DASHBOARD_URL/events" \
    -H "Content-Type: application/json" \
    -d "$JSON" >/dev/null 2>&1 || true
fi

# Локальное дублирование в progress.log проекта
LOG_FILE="$HOME/projects/$PROJECT/progress.log"
if [ -d "$HOME/projects/$PROJECT" ]; then
  echo "$(date -u +%Y-%m-%dT%H:%M:%S) [$AGENT] $MSG" >> "$LOG_FILE" 2>/dev/null || true
fi
