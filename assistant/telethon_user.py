import asyncio
import os
from functools import partial

from telethon import TelegramClient, events

import claude_client

API_ID   = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]
SESSION  = "/opt/assistant/user_session"

client = TelegramClient(SESSION, API_ID, API_HASH)

_me_id = None
_loop = None


async def _get_me_id():
    global _me_id
    if _me_id is None:
        me = await client.get_me()
        _me_id = me.id
    return _me_id




@client.on(events.NewMessage(outgoing=True, chats="me"))
async def handle_saved(event):
    """Respond in Saved Messages only when message starts with 'Клод,'."""
    text = event.text
    if not text or text.startswith("🤖"):
        return
    prefix = "клод,"
    if not text.lower().startswith(prefix):
        return
    query = text[len(prefix):].strip()
    if not query:
        return
    loop = asyncio.get_running_loop()
    reply = await loop.run_in_executor(
        None, partial(claude_client.chat, "userbot_self", query)
    )
    await client.send_message("me", f"🤖 {reply}")


async def send_to_contact(name: str, text: str) -> bool:
    """Find a contact by name and send them a message. Returns True if sent."""
    name_lower = name.lower()
    try:
        async for dialog in client.iter_dialogs():
            if dialog.is_user and dialog.name and name_lower in dialog.name.lower():
                await client.send_message(dialog.entity, text)
                return True
    except Exception as e:
        print(f"send_to_contact error: {e}")
    return False


def send_to_contact_sync(name: str, text: str) -> bool:
    """Thread-safe wrapper — call from bot thread into telethon event loop."""
    if _loop is None:
        return False
    future = asyncio.run_coroutine_threadsafe(send_to_contact(name, text), _loop)
    try:
        return future.result(timeout=15)
    except Exception as e:
        print(f"send_to_contact_sync error: {e}")
        return False


async def run():
    await client.start()
    me = await client.get_me()
    print(f"Telethon user client started as @{me.username} ({me.first_name})")
    await client.run_until_disconnected()


def run_sync():
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _loop.run_until_complete(run())
