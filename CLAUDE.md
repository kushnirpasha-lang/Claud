# CLAUDE.md — Общак (общие настройки, инфраструктура, деплой)

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
