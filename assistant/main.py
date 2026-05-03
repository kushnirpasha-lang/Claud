import threading

from dotenv import load_dotenv

load_dotenv()

import bot
import web
import telethon_user


def main() -> None:
    web_thread = threading.Thread(target=web.run, daemon=True, name="web")
    web_thread.start()
    print("Web chat started on port 8080")

    tg_thread = threading.Thread(target=telethon_user.run_sync, daemon=True, name="telethon")
    tg_thread.start()
    print("Telethon user client starting...")

    bot.run()


if __name__ == "__main__":
    main()
