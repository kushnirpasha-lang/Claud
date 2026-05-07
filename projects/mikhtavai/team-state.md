# Состояние команды MikhtavAI

## текущая_задача
Этап 2 — подключить Claude API для реального анализа изображений

## активный_маршрут
analysis — интеграция Anthropic SDK, structured output, форматирование ответа

## текущий_шаг
Ожидание старта Этапа 2

## решения
- Стек MVP: Node.js 22, TypeScript strict, grammy, pino, zod, pnpm 11
- Telegram: long polling (без webhook)
- AI: claude-sonnet-4-6 через @anthropic-ai/sdk
- Деплой: GitHub Actions + SCP + systemd на VPS
- Порт не нужен на старте; в будущем 8081 или 3000 (не 8090)
- Репозиторий: https://github.com/kushnirpasha-lang/mikhtavai (приватный)

## блокеры
Нет

## история
- 2026-05-07: проект создан, ожидает описания
- 2026-05-07: онбординг завершён, Павел дал полное описание проекта
- 2026-05-07: база знаний записана в CLAUDE.md
- 2026-05-07: TypeScript-скелет создан в /home/user/mikhtavai/, initial commit
- 2026-05-07: репо kushnirpasha-lang/mikhtavai создан и запушен ✅
- 2026-05-07: ANTHROPIC_API_KEY добавлен в GitHub Secrets ✅
- 2026-05-07: Этап 1 завершён ✅
