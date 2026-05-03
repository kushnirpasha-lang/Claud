import base64
import io
import os

from PIL import Image, ImageEnhance
from openai import OpenAI


def _enhance(img: Image.Image) -> Image.Image:
    img = ImageEnhance.Color(img).enhance(1.15)
    img = ImageEnhance.Contrast(img).enhance(1.08)
    img = ImageEnhance.Sharpness(img).enhance(1.15)
    return img


def process_product_photo(image_bytes: bytes, product_name: str, ig_format: str = "1:1") -> bytes:
    """
    Full AI pipeline:
    1. Crop to Instagram format
    2. Remove background (rembg u2netp model)
    3. AI background generation (gpt-image-1 edit fills transparent areas)
    4. Color enhancement
    Returns JPEG bytes ready for Instagram.
    """
    from image_processor import crop_to_instagram
    from rembg import remove, new_session

    # 1. Crop to Instagram format
    cropped = crop_to_instagram(image_bytes, ig_format)

    # 2. Remove background — returns RGBA PNG with transparent background
    session = new_session("u2netp")  # lightweight ~4MB model
    no_bg_bytes = remove(cropped, session=session)

    # 3. Resize to 1024x1024 (gpt-image-1 edit requirement)
    img = Image.open(io.BytesIO(no_bg_bytes)).convert("RGBA")
    img = img.resize((1024, 1024), Image.LANCZOS)
    png_buf = io.BytesIO()
    img.save(png_buf, format="PNG")

    # 4. AI fills transparent areas (background) with beautiful setting
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    prompt = (
        f"Add a professional Instagram product photography background. "
        f"Keep the {product_name} hair care product exactly as is. "
        f"Background: elegant marble or stone surface, soft diffused natural light from the side, "
        f"delicate white or pastel flowers, luxury beauty brand aesthetic, "
        f"clean minimal composition, soft shadow under the product."
    )
    response = client.images.edit(
        model="gpt-image-1",
        image=("product.png", png_buf.getvalue(), "image/png"),
        prompt=prompt,
        size="1024x1024",
        quality="medium",
    )
    result_bytes = base64.b64decode(response.data[0].b64_json)

    # 5. Color enhancement
    result_img = Image.open(io.BytesIO(result_bytes)).convert("RGB")
    result_img = _enhance(result_img)

    # 6. Final resize to Instagram optimal size
    final_size = (1080, 1080) if ig_format == "1:1" else (1080, 1350)
    result_img = result_img.resize(final_size, Image.LANCZOS)

    buf = io.BytesIO()
    result_img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()
