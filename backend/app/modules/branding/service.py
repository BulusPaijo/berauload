"""Public branding projection and filename/image helpers."""
from pathlib import Path
from io import BytesIO
import re
from PIL import Image, UnidentifiedImageError
from fastapi import HTTPException
from .defaults import DEFAULTS, FIELDS
from .models import AppBranding


def current(db):
    row = db.get(AppBranding, 1)
    values = {k: getattr(row, k) if row is not None else None for k in FIELDS}
    branding = {k: DEFAULTS[k] if v is None else v for k, v in values.items()}
    branding['logo_version'] = row.logo_version if row else 0
    branding['favicon_version'] = row.favicon_version if row else 0
    branding['has_logo'] = bool(row and row.logo_ext)
    branding['has_favicon'] = bool(row and row.favicon_ext)
    return branding


def ensure_row(db):
    row = db.get(AppBranding, 1)
    if row is None:
        row = AppBranding(id=1, logo_version=0, favicon_version=0)
        db.add(row)
        db.flush()
    return row


def slug(text):
    result = re.sub(r'[^A-Za-z0-9_]+', '_', text or '').strip('_')[:50]
    return result or 'BerauLoad'


def sheet_title(text, prefix='Data '):
    name = re.sub(r'[\\/*?:\[\]]', '_', prefix + (text or 'BerauLoad'))
    return (name[:31] or 'Data BerauLoad')


def branding_dir():
    import os
    return Path(os.getenv('UPLOAD_DIR', '/data/uploads')) / 'branding'


def image_path(kind):
    return branding_dir() / f'{kind}.png'


def decode_image(data: bytes, kind: str) -> bytes:
    max_bytes = 512 * 1024 if kind == 'logo' else 128 * 1024
    max_side = 1024 if kind == 'logo' else 256
    if not data or len(data) > max_bytes:
        raise HTTPException(422, f'{kind}: ukuran berkas terlalu besar/kosong')
    signatures = [data.startswith(b'\x89PNG\r\n\x1a\n'), data.startswith(b'\xff\xd8\xff'),
                  data.startswith(b'RIFF') and data[8:12] == b'WEBP',
                  data[:4] == b'\x00\x00\x01\x00']
    allowed = (0, 1, 2) if kind == 'logo' else (0, 2, 3)
    if not any(signatures[i] for i in allowed):
        raise HTTPException(422, 'Format tidak didukung: logo PNG/JPEG/WebP; favicon PNG/WebP/ICO')
    try:
        Image.MAX_IMAGE_PIXELS = 1024 * 1024
        with Image.open(BytesIO(data)) as image:
            if image.format not in ({'PNG', 'JPEG', 'WEBP'} if kind == 'logo'
                                    else {'PNG', 'WEBP', 'ICO'}):
                raise ValueError('Format gambar tidak didukung')
            width, height = image.size
            if width <= 0 or height <= 0 or max(width, height) > max_side:
                raise ValueError(f'Dimensi {kind} maksimal {max_side}x{max_side}')
            image.load()
            clean = image.convert('RGBA')
            if kind == 'logo':
                clean.thumbnail((512, 512), Image.Resampling.LANCZOS)
            output = BytesIO()
            clean.save(output, format='PNG', optimize=True)
            if len(output.getvalue()) > max_bytes:
                raise ValueError('Gambar hasil pemrosesan terlalu besar')
            return output.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise HTTPException(422, f'Berkas bukan gambar valid: {exc}') from exc


def save_atomically(kind, data):
    path = image_path(kind)
    path.parent.mkdir(parents=True, exist_ok=True)
    import os, tempfile
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.upload-')
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def pdf_logo(branding):
    if not branding['has_logo']:
        return None
    try:
        from reportlab.platypus import Image as PDFImage
        path = image_path('logo')
        with Image.open(path) as image:
            image.verify()
        return PDFImage(str(path), width=50, height=50, kind='proportional')
    except Exception:
        return None
