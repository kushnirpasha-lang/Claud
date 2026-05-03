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

PRODUCTS = {
    "Крем-спрей": ["200мл", "50мл"],
    "Термозащита": ["200мл", "50мл"],
    "Ламелярная вода": ["200мл", "50мл"],
}


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


def _create_folder(svc, name, parent_id):
    existing = _find_folder(svc, name, parent_id)
    if existing:
        return existing
    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    f = svc.files().create(body=meta, fields="id").execute()
    return f["id"]


def _folder_ids():
    svc = _service()
    parent = _find_folder(svc, PARENT_FOLDER)
    if not parent:
        raise RuntimeError(f"Папка '{PARENT_FOLDER}' не найдена в Drive")
    queue = _find_folder(svc, QUEUE_FOLDER, parent)
    posted = _find_folder(svc, POSTED_FOLDER, parent)
    return svc, queue, posted


def _get_folder_id(svc, parent_id, *path):
    current = parent_id
    for name in path:
        current = _find_folder(svc, name, current)
        if not current:
            return None
    return current


def create_product_structure() -> dict:
    """Create full product/size/Исходники+Обработанные folder structure."""
    svc = _service()
    parent = _find_folder(svc, PARENT_FOLDER)
    if not parent:
        raise RuntimeError(f"Папка '{PARENT_FOLDER}' не найдена")
    result = {}
    for product, sizes in PRODUCTS.items():
        product_id = _create_folder(svc, product, parent)
        result[product] = {}
        for size in sizes:
            size_id = _create_folder(svc, size, product_id)
            result[product][size] = {}
            for subfolder in ["Исходники", "Обработанные"]:
                sub_id = _create_folder(svc, subfolder, size_id)
                result[product][size][subfolder] = sub_id
    return result


def upload_to_product(product: str, size: str, folder_type: str,
                      image_bytes: bytes, mime_type: str = "image/jpeg",
                      name: str = None) -> str:
    """Upload image to product/size/folder_type. Returns file_id."""
    svc = _service()
    parent = _find_folder(svc, PARENT_FOLDER)
    folder_id = _get_folder_id(svc, parent, product, size, folder_type)
    if not folder_id:
        raise RuntimeError(f"Папка {product}/{size}/{folder_type} не найдена")
    if not name:
        ext = ".jpg" if "jpeg" in mime_type else ".png"
        name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ext
    media = MediaIoBaseUpload(io.BytesIO(image_bytes), mimetype=mime_type)
    f = svc.files().create(
        body={"name": name, "parents": [folder_id]},
        media_body=media,
        fields="id",
    ).execute()
    return f["id"]


def list_product_files(product: str, size: str, folder_type: str = "Обработанные") -> list:
    """List image files in product/size/folder_type."""
    try:
        svc = _service()
        parent = _find_folder(svc, PARENT_FOLDER)
        folder_id = _get_folder_id(svc, parent, product, size, folder_type)
        if not folder_id:
            return []
        q = (f"'{folder_id}' in parents and trashed=false and "
             f"(mimeType='image/jpeg' or mimeType='image/png' or mimeType='image/webp')")
        res = svc.files().list(q=q, fields="files(id,name,mimeType,createdTime)").execute()
        return res.get("files", [])
    except Exception as e:
        print(f"Drive list error: {e}")
        return []


def make_file_public(file_id: str) -> str:
    """Make file publicly readable. Returns direct image URL."""
    svc = _service()
    svc.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()
    return f"https://drive.google.com/uc?export=view&id={file_id}"


def remove_public_access(file_id: str) -> None:
    """Remove public read access from file."""
    svc = _service()
    try:
        perms = svc.permissions().list(fileId=file_id, fields="permissions(id,type)").execute()
        for p in perms.get("permissions", []):
            if p.get("type") == "anyone":
                svc.permissions().delete(fileId=file_id, permissionId=p["id"]).execute()
    except Exception as e:
        print(f"Drive remove public error: {e}")


def move_file_to_posted(file_id: str, mime_type: str = "image/jpeg") -> str:
    """Move any file to Выложенные with timestamp name."""
    svc, _, posted_id = _folder_ids()
    if not posted_id:
        raise RuntimeError(f"Папка '{POSTED_FOLDER}' не найдена")
    f = svc.files().get(fileId=file_id, fields="parents").execute()
    current_parents = ",".join(f.get("parents", []))
    ext = ".jpg" if "jpeg" in mime_type else ".png"
    name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ext
    svc.files().update(
        fileId=file_id,
        addParents=posted_id,
        removeParents=current_parents,
        body={"name": name},
        fields="id",
    ).execute()
    return name


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
