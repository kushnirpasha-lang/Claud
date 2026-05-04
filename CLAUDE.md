# CLAUDE.md — Контекст проекта

## Владелец
- **Имя:** Pavel (@Pavel_Kus)
- **Телефон:** +380637353733
- **Язык общения:** русский

## Сервер
- **Провайдер:** DigitalOcean VPS
- **IP:** 188.166.67.237
- **Путь к проекту:** `/opt/assistant/`
- **Сервис:** `systemctl restart assistant`
- **Файл окружения:** `/opt/assistant/.env`

## Репозиторий
- **GitHub:** `kushnirpasha-lang/Claud`
- **Рабочая ветка:** `claude/setup-digitalocean-vps-4Ij39`
- **Main ветка:** только для workflow файлов (tg-check.yml, deploy.yml)
- **Deploy:** автоматически при push в `claude/setup-digitalocean-vps-4Ij39`

## Структура ассистента (`/opt/assistant/`)
```
main.py          — точка входа, запускает бота + telethon + web
bot.py           — Telegram бот (основной интерфейс)
claude_client.py — обёртка над Anthropic API с кэшированием
config.py        — модель, системный промпт, MAX_HISTORY=15
telethon_user.py — Telethon клиент (только отправка сообщений)
trello_client.py — Trello API клиент с кэшем 5 мин
web.py           — Flask веб-интерфейс на порту 8080
requirements.txt — зависимости
```

## Telegram Bot
- **Токен:** в GitHub Secret `TELEGRAM_BOT_TOKEN`
- **Функции:** текстовые сообщения, голосовые (Whisper), отправка сообщений контактам с подтверждением

## Telegram Userbot (Telethon)
- **Аккаунт:** @Pavel_Kus (авторизован)
- **Сессия:** `/opt/assistant/user_session.session`
- **Режим:** только отправка сообщений — никаких авто-ответов, не читает Избранное
- **Re-авторизация:** через workflow `tg-check.yml` → step=request → код → step=signin + 2FA

## Правила (ОБЯЗАТЕЛЬНО соблюдать)
1. **Никаких сообщений контактам без явного ✅ от Павла**
2. **Не трогать Избранное (Saved Messages)**
3. **Весь диалог только через Telegram бота**
4. **Перед любым рискованным действием — спросить**
5. **Секреты только в GitHub Secrets, никогда в коде**

## Trello
- **Рабочая доска:** HairLove (`69f5ee59565cd64f2e9da2ff`)
- **API Key / Token:** в GitHub Secrets `TRELLO_API_KEY`, `TRELLO_TOKEN`
- **Кэш:** 5 минут, обновляется при изменениях

## API ключи (в GitHub Secrets и `/opt/assistant/.env`)
- `ANTHROPIC_API_KEY` — Claude API
- `OPENAI_API_KEY` — Whisper (голосовые сообщения)
- `TELEGRAM_BOT_TOKEN` — бот
- `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` — Telethon
- `TRELLO_API_KEY` / `TRELLO_TOKEN` — Trello
- `SSH_HOST`, `SSH_PRIVATE_KEY` — доступ к серверу
- `MY_PAT` — GitHub Personal Access Token

## Оптимизация токенов
- Модель: `claude-sonnet-4-6`
- Системный промпт: кэшируется (`cache_control: ephemeral`)
- История: 15 сообщений (MAX_HISTORY)
- Intent detection: сначала keyword pre-filter, Haiku только при совпадении
- Haiku для: intent detection, Trello команды
- Sonnet для: основной чат

## Как деплоить изменения
```bash
git add <файлы>
git commit -m "описание"
git push -u origin claude/setup-digitalocean-vps-4Ij39
# Deploy запустится автоматически (~2-3 мин)
```

## Как добавить GitHub Secret
```python
# Шифрование через PyNaCl
from nacl.public import PublicKey, SealedBox
# Pub key: JdVbhjlKXocKyyrGc8USxxESqS/53NxyLS23X3s+zzc=
# Key ID: 3380204578043523366
```

## Как проверить результат на сервере
- Через Issue #1: `kushnirpasha-lang/Claud/issues/1`
- Workflow `tg-check.yml` постит результаты туда

## Правило памяти между сессиями (ОБЯЗАТЕЛЬНО)
В конце каждой сессии или при значительных изменениях — обновить `MEMORY.md`:
1. Что нового сделано и работает
2. Какие задачи остались незавершёнными
3. Какие решения приняты
4. Любые важные детали для следующей сессии

Затем закоммитить:
```bash
git add MEMORY.md
git commit -m "memory: обновить состояние после сессии"
git push -u origin claude/update-nodejs-actions-M3RLv
```

При старте новой сессии — первым делом читать `MEMORY.md` и `CLAUDE.md`.

---

## Instagram — Настройки (исходная точка, май 2026)

### Аккаунт
- **Instagram:** `@hair_love_company`
- **Instagram User ID:** `17841424039191195`
- **Тип аккаунта:** Business ✅

### Meta Developer Portal
- **Facebook App:** HairLove (`ID: 26870095375982242`)
- **Instagram App:** HairLove-IG (`ID: 35214006608243743`)
- **App Secret Instagram:** в GitHub Secret — не хранить в коде
- **Портал:** `developers.facebook.com/apps/26870095375982242`
- **Статус приложения:** Не опубликовано (Development Mode)

### Токен доступа
- **Тип:** Instagram User Token (новый Instagram Login API)
- **GitHub Secret:** `INSTAGRAM_ACCESS_TOKEN`
- **Срок действия:** ~60 дней (нужно обновлять!)
- **Где обновить:** `developers.facebook.com/apps/26870095375982242/use_cases/customize/?use_case_enum=INSTAGRAM_BUSINESS`
  → раздел "Настройка API для входа в Inst..." → "2. Сгенерируйте маркеры доступа" → "Сгенерировать маркер" рядом с `hair_love_company`

### Разрешения (добавлены в приложении)
- `instagram_content_publish` ✅ — публикация постов
- `instagram_business_basic` ✅ — базовый доступ
- `instagram_business_content_publish` ✅ — публикация (новый API)
- `instagram_business_manage_insights` ✅ — статистика
- `instagram_manage_insights` ✅ — аналитика
- `instagram_manage_comments` ✅ — комментарии
- `pages_show_list` ✅ — список страниц
- `pages_read_engagement` ✅ — статистика страницы
- `ads_management` ✅ — управление рекламой
- `ads_read` ✅ — отчёты по рекламе

### GitHub Secrets (Instagram)
- `INSTAGRAM_ACCESS_TOKEN` — Instagram User Token (обновлять каждые ~60 дней)
- `INSTAGRAM_USER_ID` — `17841424039191195`

### API Endpoint
- **Base URL:** `https://graph.instagram.com/v21.0`
- **Создать контейнер:** `POST /v21.0/{INSTAGRAM_USER_ID}/media`
- **Опубликовать:** `POST /v21.0/{INSTAGRAM_USER_ID}/media_publish`

### Workflow файлы (все на ветке `main`)
- `ig-publish.yml` — публикация по `repository_dispatch` (event: `instagram_publish`)
- `ig-prepare.yml` — подготовка превью сессии
- `ig-diagnostic.yml` — диагностика токена (запускать вручную)
- `ig-find-id.yml` — поиск Instagram ID (запускать вручную)

### Архитектура публикации (Claude Code → Instagram)
```
1. Павел отправляет фото в Claude Code
2. Claude извлекает фото из сессии JSONL
3. Фото + caption.txt + session_id.txt → пушатся в _ig_pending/
4. ig-prepare.yml (GitHub Actions):
   - Копирует фото на VPS через SCP
   - Создаёт сессию через POST /api/instagram/session-create
5. Claude отправляет превью ссылку: http://188.166.67.237/instagram/preview/{session_id}
6. Павел открывает ссылку, нажимает "Опубликовать"
7. Браузер вызывает POST /api/instagram/session/{id}/post на VPS
8. VPS (web.py) триггерит repository_dispatch → ig-publish.yml
9. ig-publish.yml постит в Instagram через graph.instagram.com
10. Результат возвращается на VPS через mark-result endpoint
11. Браузер показывает ✅ или ❌
```

### Сессии (VPS)
- **Файл:** `/opt/assistant/ig_sessions.json` — персистентные сессии
- **Загрузки:** `/opt/assistant/static/uploads/` — фото для превью
- **Превью страница:** `http://188.166.67.237/instagram/preview/{session_id}`
