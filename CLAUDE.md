# CLAUDE.md — Общак (общие настройки, инфраструктура, деплой)

## Владелец
- **Имя:** Pavel (@Pavel_Kus)
- **Телефон:** +380637353733
- **Язык общения:** русский

## ⚠️ Правило №0 — ПАМЯТЬ КООРДИНАТОРА (ОБЯЗАТЕЛЬНО)

**После каждого ответа агента** — немедленно обновить оба файла:
- `projects/hairlove/progress.log` — одна строка: `<ISO-время> <эмодзи> [<агент>] <что сделал / что не вышло>`
- `projects/hairlove/team-state.md` — обновить `текущий_шаг`, `блокеры`, `решения` если изменились

**Формат записи в progress.log:**
```
2026-05-10T15:00 ✅ [instagram] Опубликован первый пост — cream-spray-200ml-1.png
2026-05-10T16:00 ❌ [site] Не удалось задеплоить — ошибка 403
2026-05-10T17:00 ⚠️ [coordinator] Сессия прервана, незавершённая задача: написать тексты
```

**Это правило НЕ опционально.** Без записи — следующая сессия стартует вслепую.

---

## ⚠️ Правило №1 — ОБЯЗАТЕЛЬНО
**НИКОГДА не писать Павлу "у меня нет доступа", "нет прав", "не могу найти" — не попробовав.**
Перед тем как сказать что что-то недоступно — попробовать минимум 3 способа:
1. Прямой путь (bash, read, curl)
2. Через MCP GitHub (get_file_contents, search_code, list_branches)
3. Через WebFetch / WebSearch / Agent

Если все три не сработали — написать ЧТО именно пробовал и ПОЧЕМУ не вышло. Не просто "нет доступа".

## Сервер
- **Провайдер:** DigitalOcean VPS
- **IP:** 188.166.67.237
- **Путь к проекту:** `/opt/assistant/`
- **Сервис:** `systemctl restart assistant`
- **Файл окружения:** `/opt/assistant/.env`

## Репозиторий
- **GitHub:** `kushnirpasha-lang/Claud`
- **Рабочая ветка:** `claude/obshak`
- **Main ветка:** только для workflow файлов (tg-check.yml, deploy.yml)
- **Deploy:** автоматически при push в `claude/obshak`

## Git Push — как это работает

Push настроен автоматически через `/usr/bin/git` wrapper и `pushurl` в `.git/config`.
**Ничего не нужно делать вручную при старте сессии — просто пушь как обычно.**

Если вдруг ошибка "токен не найден" или 403:
```bash
git config --global github.token $(cat /home/user/Claud/.git/pat)
```
Токен хранится в `/home/user/Claud/.git/pat` — этот файл не в git-репозитории, но сохраняется между сессиями на одной VM.

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
