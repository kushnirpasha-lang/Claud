#!/usr/bin/env bash
# Запуск Claude Code в контексте проекта через tmux
set -euo pipefail

if [ -z "${1:-}" ]; then
  echo "Использование: ./запуск.sh <имя-проекта>"
  echo ""
  echo "Доступные проекты:"
  ls -1 "$HOME/projects/" | grep -v '\.sh$' | grep -v '^_'
  exit 1
fi

ИМЯ="$1"
ПУТЬ="$HOME/projects/$ИМЯ"

if [ ! -d "$ПУТЬ" ]; then
  echo "❌ Проект «$ИМЯ» не найден в $HOME/projects/"
  echo "Создать: ~/projects/новый-проект.sh $ИМЯ"
  exit 1
fi

cd "$ПУТЬ"
export CLAUDE_PROJECT_NAME="$ИМЯ"

echo "🚀 Запускаю проект «$ИМЯ» в tmux-сессии..."
echo "   Дашборд: http://188.166.67.237/agents"
echo ""

# Присоединяемся к существующей сессии или создаём новую
tmux new-session -A -s "$ИМЯ" -e "CLAUDE_PROJECT_NAME=$ИМЯ" "cd '$ПУТЬ' && claude"
