#!/usr/bin/env python3
"""Process _pending/ folder: upload image to Drive + post to Instagram."""
import json, os, sys

sys.path.insert(0, '/opt/assistant')
os.chdir('/opt/assistant')

from dotenv import load_dotenv
load_dotenv()

import google_drive_client
import instagram_client

PENDING_DIR = '/tmp/pending_upload'

image_path = None
for ext in ['jpg', 'jpeg', 'png', 'webp']:
    c = os.path.join(PENDING_DIR, f'image.{ext}')
    if os.path.exists(c):
        image_path = c
        break

if not image_path:
    print("ERROR: no image found in pending dir")
    sys.exit(1)

with open(os.path.join(PENDING_DIR, 'meta.json')) as f:
    meta = json.load(f)

product = meta['product']
size = meta['size']
caption = meta['caption']
folder_type = meta.get('folder_type', 'Исходники')
mime = 'image/jpeg' if image_path.endswith(('.jpg', '.jpeg')) else 'image/png'

print(f"Product: {product} {size}")
with open(image_path, 'rb') as f:
    image_bytes = f.read()

file_id = google_drive_client.upload_to_product(product, size, folder_type, image_bytes, mime)
print(f"Uploaded to Drive {folder_type}: {file_id}")

public_url = google_drive_client.make_file_public(file_id)
result = instagram_client.post_photo(public_url, caption)
print(f"Posted to Instagram: {result}")

posted_name = google_drive_client.move_file_to_posted(file_id, mime)
google_drive_client.remove_public_access(file_id)
print(f"Done! Saved as: {posted_name}")
