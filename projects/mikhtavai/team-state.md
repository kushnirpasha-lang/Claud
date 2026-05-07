# Состояние команды MikhtavAI

## текущая_задача
Создать GitHub-репозиторий kushnirpasha-lang/mikhtavai и запушить скелет

## активный_маршрут
scaffold — построение базовой структуры проекта

## текущий_шаг
Шаг 2: нужен PAT для создания GitHub-репозитория и git push

## решения
- Стек MVP: Node.js 22, TypeScript strict, grammy, pino, zod, pnpm 11
- Telegram: long polling (без webhook)
- AI: claude-sonnet-4-6 через @anthropic-ai/sdk
- Деплой: GitHub Actions + SCP + systemd на VPS
- Порт не нужен на старте; в будущем 8081 или 3000 (не 8090)
- Локальный путь: /home/user/mikhtavai/ (отдельно от Claud)

## блокеры
⚠️ PAT не сохранён в ~/.gitconfig — нельзя создать репозиторий и запушить.
Нужно: git config --global github.token <PAT> (scope: repo, write)

## история
- 2026-05-07: проект создан, ожидает описания
- 2026-05-07: онбординг завершён, Павел дал полное описание проекта
- 2026-05-07: база знаний записана в CLAUDE.md
- 2026-05-07: TypeScript-скелет создан в /home/user/mikhtavai/, initial commit d5780f2
- 2026-05-07: ожидаем PAT для создания GitHub-репо и push
