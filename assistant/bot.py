import asyncio
import io
import os
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


def _detect_intent(text: str) -> dict:
    """
    Detect user intent. Returns dict with 'type' key:
    - {'type': 'send_tg', 'to': name, 'text': msg}
    - {'type': 'trello', 'action': action_text}
    - {'type': 'chat'}
    """
    import anthropic
    c = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = c.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        system=(
            "Classify user intent into one of these:\n"
            "1. Send Telegram message → respond: SEND_TG:<recipient name>|<message>\n"
            "2. Trello task (show board, add card, move card, list tasks) → respond: TRELLO:<user request verbatim>\n"
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
    """Process Trello-related request using Claude + Trello API."""
    try:
        import trello_client
        boards = trello_client.get_boards()
        if not boards:
            return "В твоём Trello нет активных досок."

        # Use the first board (or the one configured)
        board_id = os.environ.get("TRELLO_BOARD_ID", boards[0]["id"])
        board_name = next((b["name"] for b in boards if b["id"] == board_id), boards[0]["name"])
        summary = trello_client.get_board_summary(board_id)

        import anthropic
        c = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        resp = c.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            system=(
                f"Ты помощник для работы с Trello-доской '{board_name}'.\n"
                f"Текущее состояние доски:\n{summary}\n\n"
                "Отвечай кратко и по делу. Если нужно создать карточку или переместить — "
                "скажи что именно сделал. Отвечай на русском."
            ),
            messages=[{"role": "user", "content": user_request}],
        )
        return resp.content[0].text
    except Exception as e:
        print(f"Trello error: {e}")
        return f"Ошибка при работе с Trello: {e}"


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


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    app.add_handler(CallbackQueryHandler(handle_send_callback, pattern="^send_"))

    print("Telegram bot started.")
    app.run_polling(drop_pending_updates=True)
