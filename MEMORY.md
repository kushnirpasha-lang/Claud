# MEMORY.md — Текущее состояние

## Последнее обновление
2026-05-04

## Что сделано и работает ✅
- VPS настроен, сервис `assistant` запущен
- Telegram бот работает
- Telethon авторизован как @Pavel_Kus (SUCCESS_2FA)
- Trello подключён, доска HairLove видна (`69f5ee59565cd64f2e9da2ff`)
- Prompt caching включён — экономия ~90% на системном промпте
- Keyword pre-filter — Haiku вызывается только при необходимости
- Авто-ответы на входящие сообщения ОТКЛЮЧЕНЫ
- **Instagram постинг работает** ✅
  - Токен: Instagram User Token (Instagram Login API), в секрете `INSTAGRAM_ACCESS_TOKEN`
  - User ID: `17841424039191195` (@hair_love_company)
  - API: `graph.instagram.com/v21.0`
  - Workflow: `ig-publish.yml` на ветке `main` (repository_dispatch)
  - Токен нужно обновлять каждые ~60 дней в Meta Developer Portal
- **Гуманизатор** сохранён как скилл `.claude/commands/humanize.md`
- **Instagram промпт** обновлён с правилами живого текста (без ИИ-штампов)
- `UPLOAD_DIR` и `VPS_URL` определены в `web.py`
- `MY_PAT` добавлен в VPS `.env` через `deploy.yml`

## Архитектура агентов (в процессе построения)
```
Павел (главный оркестратор)
└── Агент HairLove
    ├── Инста ✅ (постинг работает)
    │   ├── Постинг (ig-publish workflow)
    │   └── Генерация текста (промпт с гуманизатором)
    ├── Стратегия 🔲
    ├── Сайт 🔲
    ├── Анализ конкурентов 🔲
    └── Реклама 🔲
```

## Незавершённые задачи
- [ ] Проверить работу команд Trello через бота
- [ ] Проверить голосовые сообщения (OpenAI Whisper)
- [ ] Проверить отправку сообщений контакту через бота
- [ ] Задать условия для текста Instagram (голос бренда, хэштеги, структура)
- [ ] Агент HairLove: Стратегия, Сайт, Реклама, Анализ конкурентов

## Известные проблемы
- OpenAI API ключ (`sk-proj-mrU...`) — проверить есть ли в `.env` на сервере
- Если голосовые не работают — скорее всего именно это

## Решения принятые
- Instagram токен: Instagram Login API (новый), не Facebook Login (старый)
- Постинг через GitHub Actions (repository_dispatch), не напрямую с VPS
- Сессии превью персистентны (`ig_sessions.json` на диске)
- Гуманизатор применяется ко всем текстам HairLove
- Секреты только в GitHub Secrets, никогда в коде

## Рабочие ветки
- Основная рабочая: `claude/update-nodejs-actions-M3RLv`
- Deploy триггерится при push в эту ветку
- Workflow файлы (`ig-publish.yml` и др.) — на ветке `main`

## Важные команды
```bash
# Перезапуск сервиса на VPS
systemctl restart assistant

# Логи
journalctl -u assistant -n 50

# Git push (токен уже в remote URL)
git push -u origin claude/update-nodejs-actions-M3RLv
```

## Превью Instagram (последняя тестовая сессия)
- URL: `http://188.166.67.237/instagram/preview/c8b0b1e9017f4c108db7c41c9a25be44`
- Последний успешный пост: Post ID `17926264809292098`
