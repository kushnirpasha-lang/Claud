import asyncio, os, sys
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

CODE = sys.argv[1] if len(sys.argv) > 1 else ""

async def main():
    api_id   = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]
    phone_hash = open("/tmp/tg_hash").read().strip()
    c = TelegramClient("/opt/assistant/user_session", api_id, api_hash)
    await c.connect()
    try:
        await c.sign_in("+380637353733", CODE, phone_code_hash=phone_hash)
        me = await c.get_me()
        print(f"SUCCESS: {me.first_name} @{me.username}")
    except SessionPasswordNeededError:
        print("2FA_REQUIRED")
    except Exception as e:
        print(f"ERROR: {e}")
    await c.disconnect()

asyncio.run(main())
