import asyncio
import os

from telethon import TelegramClient

API_ID   = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]
SESSION  = "/opt/assistant/user_session"

client = TelegramClient(SESSION, API_ID, API_HASH)

_loop = None


async def send_to_saved(text: str) -> bool:
    """Send message to Saved Messages (me). Only allowed destination."""
    try:
        await client.send_message('me', text)
        return True
    except Exception as e:
        print(f"send_to_saved error: {e}")
        return False


def send_to_saved_sync(text: str) -> bool:
    if _loop is None:
        return False
    future = asyncio.run_coroutine_threadsafe(send_to_saved(text), _loop)
    try:
        return future.result(timeout=15)
    except Exception as e:
        print(f"send_to_saved_sync error: {e}")
        return False


async def run():
    await client.start()
    me = await client.get_me()
    print(f"Telethon started as @{me.username} ({me.first_name}) — Saved Messages only")
    await client.run_until_disconnected()


def run_sync():
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _loop.run_until_complete(run())
