import threading
import time

from dotenv import load_dotenv

load_dotenv()

import bot
import web
import telethon_user


def _drive_queue_loop() -> None:
    """Check Google Drive 'Очередь' folder every 5 minutes and auto-post to Instagram."""
    time.sleep(60)
    while True:
        try:
            import uuid
            import os
            import google_drive_client
            import claude_client
            import instagram_client

            files = google_drive_client.list_queue_files()
            for f in files:
                try:
                    image_bytes = google_drive_client.download_file(f["id"])
                    mime = f.get("mimeType", "image/jpeg")
                    caption = claude_client.generate_instagram_caption(image_bytes, mime)

                    temp_name = uuid.uuid4().hex + ".jpg"
                    temp_path = f"/opt/assistant/static/uploads/{temp_name}"
                    os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                    with open(temp_path, "wb") as fp:
                        fp.write(image_bytes)

                    vps_url = os.environ.get("VPS_URL", "http://188.166.67.237")
                    instagram_client.post_photo(f"{vps_url}/static/uploads/{temp_name}", caption)
                    google_drive_client.move_to_posted(f["id"], mime)

                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass

                    print(f"Drive queue: posted {f['name']} to Instagram")
                except Exception as e:
                    print(f"Drive queue: error on {f['name']}: {e}")
        except Exception as e:
            print(f"Drive queue loop error: {e}")

        time.sleep(300)


def main() -> None:
    web_thread = threading.Thread(target=web.run, daemon=True, name="web")
    web_thread.start()
    print("Web chat started on port 8080")

    tg_thread = threading.Thread(target=telethon_user.run_sync, daemon=True, name="telethon")
    tg_thread.start()
    print("Telethon user client starting...")

    drive_thread = threading.Thread(target=_drive_queue_loop, daemon=True, name="drive-queue")
    drive_thread.start()
    print("Drive queue checker started (every 5 min)")

    bot.run()


if __name__ == "__main__":
    main()
