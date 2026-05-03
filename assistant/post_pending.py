#!/usr/bin/env python3
"""Process _pending/ folder: post image to Instagram via VPS static URL."""
import json, os, sys, uuid, shutil

sys.path.insert(0, '/opt/assistant')
os.chdir('/opt/assistant')

from dotenv import load_dotenv
load_dotenv()

import instagram_client

PENDING_DIR = '/tmp/pending_upload'
UPLOADS_DIR = '/opt/assistant/static/uploads'
VPS_URL = os.environ.get('VPS_URL', 'http://188.166.67.237')

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

caption = meta['caption']
print(f"Product: {meta['product']} {meta['size']}")

# Copy to VPS static uploads for public URL
os.makedirs(UPLOADS_DIR, exist_ok=True)
temp_name = f"{uuid.uuid4().hex}.jpg"
temp_path = os.path.join(UPLOADS_DIR, temp_name)
shutil.copy2(image_path, temp_path)

public_url = f"{VPS_URL}/static/uploads/{temp_name}"
print(f"Public URL: {public_url}")

try:
    result = instagram_client.post_photo(public_url, caption)
    print(f"Posted to Instagram: {result}")
finally:
    try:
        os.remove(temp_path)
    except Exception:
        pass

print("Done!")
