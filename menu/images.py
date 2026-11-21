"""Image handling for uploaded product photos."""
from io import BytesIO
from pathlib import PurePath

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.text import slugify
from PIL import Image, ImageOps

MAX_SIDE = 1200           # longest side after resizing (px)
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def optimize_image(upload, max_side=MAX_SIDE, quality=85):
    """Return a web-friendly JPEG: orientation fixed, resized, transparency flattened.

    Phone photos are often 4000px+ and several MB; shrinking them keeps the menu fast.
    """
    img = Image.open(upload)
    img.load()
    img = ImageOps.exif_transpose(img)
    if img.mode in ('RGBA', 'LA', 'P'):
        img = img.convert('RGBA')
        flat = Image.new('RGB', img.size, 'white')
        flat.paste(img, mask=img.getchannel('A'))
        img = flat
    else:
        img = img.convert('RGB')
    img.thumbnail((max_side, max_side), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, 'JPEG', quality=quality, optimize=True, progressive=True)
    stem = slugify(PurePath(getattr(upload, 'name', 'photo')).stem) or 'photo'
    return SimpleUploadedFile(f'{stem}.jpg', buf.getvalue(), content_type='image/jpeg')
