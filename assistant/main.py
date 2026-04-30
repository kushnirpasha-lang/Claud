import threading

from dotenv import load_dotenv

load_dotenv()

import bot
import web


def main() -> None:
    web_thread = threading.Thread(target=web.run, daemon=True, name="web")
    web_thread.start()
    print("Web chat started on port 8080")

    bot.run()  # blocking, runs in main thread


if __name__ == "__main__":
    main()
