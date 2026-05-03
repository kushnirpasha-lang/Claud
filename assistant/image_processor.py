import io
from PIL import Image


def crop_to_instagram(image_bytes: bytes, format: str = "1:1") -> bytes:
    """Smart center crop + resize to Instagram format. format: '1:1' or '4:5'"""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = img.size

    target_ratio = 1.0 if format == "1:1" else 4 / 5
    current_ratio = w / h

    if current_ratio > target_ratio:
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    elif current_ratio < target_ratio:
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))

    target_size = (1080, 1080) if format == "1:1" else (1080, 1350)
    img = img.resize(target_size, Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()
