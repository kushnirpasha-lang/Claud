import io
import json
import os
from datetime import datetime

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]
QUEUE_FOLDER = "Очередь"
POSTED_FOLDER = "Выложенные"
PARENT_FOLDER = "HairLove Instagram"


def _service():
    info = json.loads(open("/opt/assistant/google_service_account.json").read())
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _find_folder(svc, name, parent_id=None):
    q = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        q += f" and '{parent_id}' in parents"
    res = svc.files().list(q=q, fields="files(id)").execute()
    files = res.get("files", [])
    return files[0]["id"] if files else None


def _folder_ids():
    svc = _service()
    parent = _find_folder(svc, PARENT_FOLDER)
    if not parent:
        raise RuntimeError(f"Папка '{PARENT_FOLDER}' не найдена в Drive")
    queue = _find_folder(svc, QUEUE_FOLDER, parent)
    posted = _find_folder(svc, POSTED_FOLDER, parent)
    return svc, queue, posted


def list_queue_files() -> list:
    try:
        svc, queue_id, _ = _folder_ids()
        if not queue_id:
            return []
        q = (f"'{queue_id}' in parents and trashed=false and "
             f"(mimeType='image/jpeg' or mimeType='image/png' or mimeType='image/webp')")
        res = svc.files().list(q=q, fields="files(id,name,mimeType)").execute()
        return res.get("files", [])
    except Exception as e:
        print(f"Drive list error: {e}")
        return []


def download_file(file_id: str) -> bytes:
    svc = _service()
    req = svc.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    dl = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _, done = dl.next_chunk()
    return buf.getvalue()


def move_to_posted(file_id: str, mime_type: str = "image/jpeg") -> str:
    svc, queue_id, posted_id = _folder_ids()
    if not posted_id:
        raise RuntimeError(f"Папка '{POSTED_FOLDER}' не найдена")
    ext = ".jpg" if "jpeg" in mime_type else ".png"
    name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ext
    svc.files().update(
        fileId=file_id,
        addParents=posted_id,
        removeParents=queue_id,
        body={"name": name},
        fields="id",
    ).execute()
    return name


def upload_to_posted(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    svc, _, posted_id = _folder_ids()
    if not posted_id:
        raise RuntimeError(f"Папка '{POSTED_FOLDER}' не найдена")
    ext = ".jpg" if "jpeg" in mime_type else ".png"
    name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ext
    media = MediaIoBaseUpload(io.BytesIO(image_bytes), mimetype=mime_type)
    svc.files().create(
        body={"name": name, "parents": [posted_id]},
        media_body=media,
        fields="id",
    ).execute()
    return name
