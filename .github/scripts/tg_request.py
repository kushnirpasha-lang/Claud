import asyncio, os, sys
from telethon import TelegramClient

async def main():
    api_id   = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]
    c = TelegramClient("/opt/assistant/user_session", api_id, api_hash)
    await c.connect()
    if await c.is_user_authorized():
        me = await c.get_me()
        print(f"ALREADY_AUTH: {me.first_name} @{me.username}")
    else:
        sent = await c.send_code_request("+380637353733")
        open("/tmp/tg_hash", "w").write(sent.phone_code_hash)
        print("CODE_SENT to +380637353733, hash saved")
    await c.disconnect()

asyncio.run(main())
