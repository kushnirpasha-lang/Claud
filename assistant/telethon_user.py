import asyncio
import os

from telethon import TelegramClient

API_ID   = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]
SESSION  = "/opt/assistant/user_session"

client = TelegramClient(SESSION, API_ID, API_HASH)

_loop = None


async def send_to_contact(name: str, text: str) -> bool:
    """Find contact by name and send message. Returns True if sent."""
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
    print(f"Telethon started as @{me.username} ({me.first_name}) — listen-only mode OFF")
    await client.run_until_disconnected()


def run_sync():
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _loop.run_until_complete(run())
