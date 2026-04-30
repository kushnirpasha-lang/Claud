import asyncio
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

WELCOME = (
    "Привет! Я твой личный ИИ-ассистент 🤖\n\n"
    "Задавай любые вопросы — ищу, анализирую, пишу тексты, "
    "помогаю с бизнесом и техникой.\n\n"
    "Команды:\n"
    "/new — начать новый разговор\n"
    "/help — что я умею"
)

HELP = (
    "Я умею:\n"
    "• Искать информацию и сравнивать варианты\n"
    "• Писать тексты, посты, письма, рекламу\n"
    "• Помогать с сайтами (структура, SEO, UX)\n"
    "• Развивать бизнес и соцсети\n"
    "• Решать технические задачи (VPS, боты, API)\n"
    "• Анализировать и давать рекомендации\n\n"
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


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = f"tg_{update.effective_user.id}"
    text = update.message.text

    stop_event = asyncio.Event()
    typing_task = asyncio.create_task(
        _keep_typing(context, update.effective_chat.id, stop_event)
    )

    try:
        loop = asyncio.get_running_loop()
        reply = await loop.run_in_executor(None, partial(claude_client.chat, uid, text))

        stop_event.set()
        typing_task.cancel()

        # Telegram message limit is 4096 chars
        for i in range(0, len(reply), 4096):
            await update.message.reply_text(reply[i : i + 4096])

    except Exception as exc:
        stop_event.set()
        typing_task.cancel()
        print(f"Error for user {uid}: {exc}")
        await update.message.reply_text(
            "Что-то пошло не так. Попробуй ещё раз или напиши /new"
        )


def run() -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("new", cmd_new))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Telegram bot started.")
    app.run_polling(drop_pending_updates=True)
