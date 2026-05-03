import asyncio
import io
import os
import uuid
from functools import partial

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import claude_client

# {user_id: {"to": contact_name, "text": message_text}}
_pending_sends: dict = {}

# {user_id: {"photo_bytes": bytes, "mime_type": str, "caption": str, "waiting_text": bool}}
_pending_ig: dict[int, dict] = {}


def _ig_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Опубликовать", callback_data="ig_post")],
        [
            InlineKeyboardButton("🔄 Новый текст", callback_data="ig_regen"),
            InlineKeyboardButton("✏️ Изменить", callback_data="ig_edit"),
        ],
        [InlineKeyboardButton("❌ Отмена", callback_data="ig_cancel")],
    ])

WELCOME = (
    "Привет! Я твой личный ИИ-ассистент 🤖\n\n"
    "Задавай вопросы или отправляй голосовые команды.\n\n"
    "Примеры:\n"
    "• «Отправь Максу Маркову: встречаемся в 18:00»\n"
    "• «Что такое квантовая физика?»\n\n"
    "Команды:\n"
    "/new — начать новый разговор\n"
    "/help — что я умею"
)

HELP = (
    "Я умею:\n"
    "• Отвечать на вопросы и анализировать\n"
    "• Писать тексты, посты, письма\n"
    "• Принимать голосовые команды 🎤\n"
    "• Отправлять сообщения твоим Telegram-контактам\n\n"
    "Голосовые: просто запиши голосовое — расшифрую и выполню.\n\n"
    "/new — очистить историю разговора"
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME)


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = f"tg_{update.effective_user.id}"
    claude_client.clear(uid)
    await update.message.reply_text("Начинаем с чистого листа! Чем могу помочь?")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP)


async def _keep_typing(context: ContextTypes.DEFAULT_TYPE, chat_id: int, stop: asyncio.Event) -> None:
    while not stop.is_set():
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        try:
            await asyncio.wait_for(asyncio.shield(stop.wait()), timeout=4)
        except asyncio.TimeoutError:
            pass


def _transcribe_voice_sync(file_bytes: bytes) -> str:
    import openai
    c = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    audio_file = io.BytesIO(file_bytes)
    audio_file.name = "voice.ogg"
    result = c.audio.transcriptions.create(model="whisper-1", file=audio_file, language="ru")
    return result.text


_SEND_KEYWORDS = ("отправь", "напиши", "передай", "скажи", "пошли", "send")
_TRELLO_KEYWORDS = ("trello", "трелло", "доска", "карточк", "задач", "колонк", "добавь задачу",
                    "перемести", "покажи задачи", "что в работе", "что сделано")


def _quick_intent(text: str) -> str | None:
    """Fast keyword check — returns 'send_tg', 'trello', or None (=needs AI)."""
    tl = text.lower()
    if any(k in tl for k in _TRELLO_KEYWORDS):
        return "trello"
    if any(k in tl for k in _SEND_KEYWORDS):
        return "maybe_send"
    return None


def _detect_intent(text: str) -> dict:
    """AI intent detection — only called when keywords suggest non-chat intent."""
    import anthropic
    c = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = c.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        system=(
            "Classify user intent into one of these:\n"
            "1. Send Telegram message to someone → respond: SEND_TG:<recipient name>|<message>\n"
            "2. Trello task (show board, add/move/delete card, list tasks) → respond: TRELLO:<user request verbatim>\n"
            "3. Anything else → respond: CHAT\n"
            "Respond with ONLY one of these formats, nothing else."
        ),
        messages=[{"role": "user", "content": text}],
    )
    result = resp.content[0].text.strip()
    if result.startswith("SEND_TG:"):
        parts = result[8:].split("|", 1)
        if len(parts) == 2:
            return {"type": "send_tg", "to": parts[0].strip(), "text": parts[1].strip()}
    elif result.startswith("TRELLO:"):
        return {"type": "trello", "action": result[7:].strip()}
    return {"type": "chat"}


def _handle_trello(uid: str, user_request: str) -> str:
    """Process Trello request: parse action with Haiku, execute via API, return result."""
    try:
        import trello_client
        summary = trello_client.get_board_summary()

        import anthropic
        c = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

        # Ask Haiku to parse the action
        resp = c.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=(
                "Ты менеджер Trello-доски HairLove. Текущее состояние:\n"
                f"{summary}\n\n"
                "Определи что нужно сделать и ответь ТОЛЬКО одной из команд:\n"
                "SHOW — показать доску\n"
                "CREATE:<колонка>|<название карточки> — создать карточку\n"
                "MOVE:<название карточки>|<колонка назначения> — переместить\n"
                "DELETE:<название карточки> — удалить карточку\n"
                "CHAT:<ответ пользователю> — просто ответить"
            ),
            messages=[{"role": "user", "content": user_request}],
        )
        cmd = resp.content[0].text.strip()

        if cmd == "SHOW" or cmd.startswith("SHOW"):
            fresh = trello_client.get_board_summary(force=True)
            return f"📋 *HairLove*\n{fresh}"

        elif cmd.startswith("CREATE:"):
            parts = cmd[7:].split("|", 1)
            if len(parts) == 2:
                col, name = parts[0].strip(), parts[1].strip()
                trello_client.create_card(col, name)
                return f"✅ Карточка «{name}» добавлена в «{col}»"
            return "Не понял что создать. Уточни колонку и название."

        elif cmd.startswith("MOVE:"):
            parts = cmd[5:].split("|", 1)
            if len(parts) == 2:
                card, col = parts[0].strip(), parts[1].strip()
                ok = trello_client.move_card(card, col)
                return f"✅ «{card}» перемещена в «{col}»" if ok else f"❌ Карточка «{card}» не найдена"
            return "Не понял что переместить."

        elif cmd.startswith("DELETE:"):
            name = cmd[7:].strip()
            ok = trello_client.delete_card(name)
            return f"✅ Карточка «{name}» удалена" if ok else f"❌ Карточка «{name}» не найдена"

        elif cmd.startswith("CHAT:"):
            return cmd[5:].strip()

        return cmd  # fallback

    except Exception as e:
        print(f"Trello error: {e}")
        return f"Ошибка Trello: {e}"


async def cmd_trello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        import trello_client
        boards = trello_client.get_boards()
        if not boards:
            await update.message.reply_text("В твоём Trello нет активных досок.")
            return
        board_id = os.environ.get("TRELLO_BOARD_ID", boards[0]["id"])
        summary = trello_client.get_board_summary(board_id)
        board_name = next((b["name"] for b in boards if b["id"] == board_id), boards[0]["name"])
        await update.message.reply_text(f"📋 *{board_name}*\n{summary}", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")


async def _process_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    uid = f"tg_{update.effective_user.id}"
    stop_event = asyncio.Event()
    typing_task = asyncio.create_task(
        _keep_typing(context, update.effective_chat.id, stop_event)
    )
    try:
        loop = asyncio.get_running_loop()

        # Fast keyword check first — skip Haiku call for plain chat (~80% of messages)
        quick = _quick_intent(text)
        if quick is None:
            intent = {"type": "chat"}
        else:
            intent = await loop.run_in_executor(None, partial(_detect_intent, text))

        if intent["type"] == "send_tg":
            contact_name, msg_text = intent["to"], intent["text"]
            _pending_sends[update.effective_user.id] = {"to": contact_name, "text": msg_text}
            stop_event.set()
            typing_task.cancel()
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Отправить", callback_data="send_confirm"),
                InlineKeyboardButton("❌ Отмена", callback_data="send_cancel"),
            ]])
            await update.message.reply_text(
                f"📤 Готово отправить *{contact_name}*:\n\n_{msg_text}_",
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
            return

        if intent["type"] == "trello":
            trello_reply = await loop.run_in_executor(None, partial(_handle_trello, uid, text))
            stop_event.set()
            typing_task.cancel()
            for i in range(0, len(trello_reply), 4096):
                await update.message.reply_text(trello_reply[i:i + 4096])
            return

        reply = await loop.run_in_executor(None, partial(claude_client.chat, uid, text))
        stop_event.set()
        typing_task.cancel()
        for i in range(0, len(reply), 4096):
            await update.message.reply_text(reply[i:i + 4096])

    except Exception as exc:
        stop_event.set()
        typing_task.cancel()
        print(f"Error for user {uid}: {exc}")
        await update.message.reply_text("Что-то пошло не так. Попробуй ещё раз или /new")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    msg = await update.message.reply_text("📸 Генерирую подпись для Instagram...")

    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_bytes = bytes(await file.download_as_bytearray())

    loop = asyncio.get_running_loop()
    try:
        caption = await loop.run_in_executor(
            None,
            partial(claude_client.generate_instagram_caption, file_bytes, "image/jpeg", ""),
        )
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка генерации подписи: {e}")
        return

    _pending_ig[uid] = {"photo_bytes": file_bytes, "mime_type": "image/jpeg",
                        "caption": caption, "waiting_text": False}
    await msg.edit_text(
        f"📝 *Подпись для Instagram:*\n\n{caption}",
        parse_mode="Markdown",
        reply_markup=_ig_keyboard(),
    )


async def handle_ig_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    pending = _pending_ig.get(uid)

    if not pending:
        await query.edit_message_text("❌ Нет активного поста. Отправь фото заново.")
        return

    if query.data == "ig_post":
        await query.edit_message_text("📤 Публикуем в Instagram...")
        loop = asyncio.get_running_loop()
        try:
            def _upload_and_post():
                import instagram_client
                filename = uuid.uuid4().hex + ".jpg"
                upload_dir = os.path.join(os.path.dirname(__file__), "static", "uploads")
                os.makedirs(upload_dir, exist_ok=True)
                with open(os.path.join(upload_dir, filename), "wb") as f:
                    f.write(pending["photo_bytes"])
                vps_url = os.environ.get("VPS_URL", "http://188.166.67.237")
                public_url = f"{vps_url}/static/uploads/{filename}"
                return instagram_client.post_photo(public_url, pending["caption"])

            result = await loop.run_in_executor(None, _upload_and_post)
            _pending_ig.pop(uid, None)
            await query.edit_message_text(
                f"✅ Опубликовано в @hair_love_company!\nID: {result.get('id', '—')}"
            )
        except Exception as e:
            await query.edit_message_text(
                f"❌ Ошибка публикации: {e}\n\n{pending['caption']}",
                reply_markup=_ig_keyboard(),
            )

    elif query.data == "ig_regen":
        await query.edit_message_text("🔄 Генерирую новую подпись...")
        loop = asyncio.get_running_loop()
        try:
            caption = await loop.run_in_executor(
                None,
                partial(claude_client.generate_instagram_caption,
                        pending["photo_bytes"], pending["mime_type"], ""),
            )
            pending["caption"] = caption
            await query.edit_message_text(
                f"📝 *Новая подпись:*\n\n{caption}",
                parse_mode="Markdown",
                reply_markup=_ig_keyboard(),
            )
        except Exception as e:
            await query.edit_message_text(
                f"❌ Ошибка: {e}\n\n{pending['caption']}",
                reply_markup=_ig_keyboard(),
            )

    elif query.data == "ig_edit":
        pending["waiting_text"] = True
        await query.edit_message_text(
            f"✏️ *Текущая подпись:*\n\n{pending['caption']}\n\n📝 Отправь новый текст:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Отмена", callback_data="ig_cancel")]
            ]),
        )

    elif query.data == "ig_cancel":
        _pending_ig.pop(uid, None)
        await query.edit_message_text("❌ Публикация отменена.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    pending = _pending_ig.get(uid)
    if pending and pending.get("waiting_text"):
        pending["waiting_text"] = False
        pending["caption"] = update.message.text
        await update.message.reply_text(
            f"📝 *Обновлённая подпись:*\n\n{pending['caption']}",
            parse_mode="Markdown",
            reply_markup=_ig_keyboard(),
        )
        return
    await _process_text(update, context, update.message.text)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        voice_file = await update.message.voice.get_file()
        file_bytes = await voice_file.download_as_bytearray()
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, partial(_transcribe_voice_sync, bytes(file_bytes)))
        await update.message.reply_text(f"🎤 _{text}_", parse_mode="Markdown")
        await _process_text(update, context, text)
    except Exception as exc:
        print(f"Voice error: {exc}")
        await update.message.reply_text("Не смог распознать голосовое. Попробуй ещё раз.")


async def handle_send_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    pending = _pending_sends.pop(uid, None)

    if query.data == "send_confirm" and pending:
        try:
            import telethon_user
            loop = asyncio.get_running_loop()
            ok = await loop.run_in_executor(
                None,
                partial(telethon_user.send_to_contact_sync, pending["to"], pending["text"])
            )
            if ok:
                await query.edit_message_text(
                    f"✅ Сообщение отправлено *{pending['to']}*", parse_mode="Markdown"
                )
            else:
                await query.edit_message_text(
                    f"❌ Контакт *{pending['to']}* не найден в Telegram", parse_mode="Markdown"
                )
        except Exception as exc:
            print(f"Send callback error: {exc}")
            await query.edit_message_text("❌ Ошибка при отправке сообщения")
    else:
        await query.edit_message_text("❌ Отменено")


def run() -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("new", cmd_new))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("trello", cmd_trello))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_send_callback, pattern="^send_"))
    app.add_handler(CallbackQueryHandler(handle_ig_callback, pattern="^ig_"))

    print("Telegram bot started.")
    app.run_polling(drop_pending_updates=True)
