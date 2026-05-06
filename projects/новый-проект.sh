#!/usr/bin/env bash
# Создание нового проекта из шаблона
set -euo pipefail

if [ -z "${1:-}" ]; then
  echo "Использование: ./новый-проект.sh <имя> [github-username/repo]"
  exit 1
fi

ИМЯ="$1"
REMOTE="${2:-}"
ПУТЬ="$HOME/projects/$ИМЯ"
ШАБЛОН="$HOME/projects/_шаблон"

[ -d "$ПУТЬ" ] && { echo "❌ $ПУТЬ уже существует"; exit 1; }
[ ! -d "$ШАБЛОН" ] && { echo "❌ Шаблон не найден: $ШАБЛОН"; exit 1; }

echo "🌱 Создаю проект «$ИМЯ»..."

cp -R "$ШАБЛОН" "$ПУТЬ"

# Подставляем имя проекта во все файлы
find "$ПУТЬ" -type f -name "*.md" -exec sed -i "s|<ИМЯ_ПРОЕКТА>|$ИМЯ|g" {} \;
find "$ПУТЬ" -type f -name "*.json" -exec sed -i "s|<ИМЯ_ПРОЕКТА>|$ИМЯ|g" {} \;

cd "$ПУТЬ"
git init -q
git add .
git commit -q -m "🌱 инициализация проекта $ИМЯ"

if [ -n "$REMOTE" ]; then
  git remote add origin "git@github.com:$REMOTE.git"
  echo "🔗 Remote: git@github.com:$REMOTE.git"
fi

# Регистрация проекта в дашборде
bash ~/.claude/событие.sh "$ИМЯ" coordinator start "проект создан" 2>/dev/null || true

echo ""
echo "✅ Проект «$ИМЯ» готов: $ПУТЬ"
echo ""
echo "Следующие шаги:"
echo "  1. Заполни knowledge/ — компания, продукт, аудитория, бренд"
echo "  2. Запуск: ~/projects/запуск.sh $ИМЯ"
echo "  3. Внутри Claude: /status для состояния, /full-cycle для полного цикла"
