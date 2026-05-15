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

CHAT_ID_FILE = "/opt/assistant/chat_id.txt"

WELCOME = (
    "Привет! Я твой личный ИИ-ассистент 🤖\n\n"
    "Задавай вопросы или отправляй голосовыхверсии команды.\n\n"
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
