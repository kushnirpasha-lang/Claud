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


async def _get_me_id():
    global _me_id
    if _me_id is None:
        me = await client.get_me()
        _me_id = me.id
    return _me_id


@client.on(events.NewMessage(incoming=True))
async def handle_incoming(event):
    """Reply with AI when someone sends a private message to the user."""
    if not event.is_private:
        return
    me_id = await _get_me_id()
    # Skip messages from bots and from self (handled separately)
    if event.sender_id == me_id:
        return
    text = event.text
    if not text:
        return

    loop = asyncio.get_running_loop()
    uid  = f"userbot_{event.sender_id}"
    reply = await loop.run_in_executor(None, partial(claude_client.chat, uid, text))
    await event.reply(reply)


@client.on(events.NewMessage(outgoing=True, chats="me"))
async def handle_saved(event):
    """Use Saved Messages as a personal AI chat."""
    text = event.text
    if not text or text.startswith("🤖"):
        return

    loop  = asyncio.get_running_loop()
    reply = await loop.run_in_executor(
        None, partial(claude_client.chat, "userbot_self", text)
    )
    await client.send_message("me", f"🤖 {reply}")


async def run():
    await client.start()
    me = await client.get_me()
    print(f"Telethon user client started as @{me.username} ({me.first_name})")
    await client.run_until_disconnected()


def run_sync():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run())
