import asyncio
import io
import os
from functools import partial

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import claude_client

CHAT_ID_FILE = "/opt/assistant/chat_id.txt"

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


def _save_chat_id(chat_id: int) -> None:
    try:
        with open(CHAT_ID_FILE, "w") as f:
            f.write(str(chat_id))
    except Exception:
        pass


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _save_chat_id(update.effective_chat.id)
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


_TRELLO_KEYWORDS = ("trello", "трелло", "доска", "карточк", "задач", "колонк", "добавь задачу",
                    "перемести", "покажи задачи", "что в работе", "что сделано")


def _quick_intent(text: str) -> str | None:
    tl = text.lower()
    if any(k in tl for k in _TRELLO_KEYWORDS):
        return "trello"
    return None


def _detect_intent(text: str) -> dict:
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
    try:
        import trello_client
        summary = trello_client.get_board_summary()

        import anthropic
        c = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

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
        return cmd
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
    _save_chat_id(update.effective_chat.id)
    uid = f"tg_{update.effective_user.id}"
    stop_event = asyncio.Event()
    typing_task = asyncio.create_task(
        _keep_typing(context, update.effective_chat.id, stop_event)
    )
    try:
        loop = asyncio.get_running_loop()

        quick = _quick_intent(text)
        if quick is None:
            intent = {"type": "chat"}
        else:
            intent = await loop.run_in_executor(None, partial(_detect_intent, text))

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




def run() -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("new", cmd_new))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("trello", cmd_trello))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    print("Telegram bot started.")
    app.run_polling(drop_pending_updates=True)
