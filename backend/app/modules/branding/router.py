"""Public identity reads and admin-only audited branding changes."""
import hashlib
import re
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.orm import Session
from ...db import AuditLog, User, get_db, now
from ...security import require
from .defaults import FIELDS, TEXT_LIMITS
from .service import current, ensure_row, decode_image, save_atomically, image_path

router = APIRouter(prefix='/api/branding', tags=['Branding'])
ICON = Path(__file__).with_name('default_favicon.svg')


def contrast(hex_color):
    channels = [int(hex_color[i:i+2], 16) / 255 for i in (1, 3, 5)]
    srgb = [x / 12.92 if x <= .04045 else ((x+.055)/1.055)**2.4 for x in channels]
    luminance = sum(v * w for v, w in zip(srgb, (.2126, .7152, .0722)))
    return 1.05 / (luminance + .05)


class BrandingInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    app_name: str | None = None
    app_short_name: str | None = None
    tagline: str | None = None
    login_eyebrow: str | None = None
    login_welcome: str | None = None
    login_description: str | None = None
    login_button_text: str | None = None
    login_footnote: str | None = None
    organization_name: str | None = None
    footer_text: str | None = None
    color_primary: str | None = None
    color_accent: str | None = None

    @field_validator(*TEXT_LIMITS.keys())
    @classmethod
    def text_valid(cls, value, info):
        if value is None:
            return None
        value = value.strip()
        if len(value) > TEXT_LIMITS[info.field_name]:
            raise ValueError('Teks terlalu panjang')
        if any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in value):
            raise ValueError('Karakter kontrol tidak diizinkan')
        if info.field_name == 'app_name' and not value:
            raise ValueError('Nama aplikasi tidak boleh kosong')
        return value or None

    @field_validator('color_primary', 'color_accent')
    @classmethod
    def color_valid(cls, value, info):
        if value is None:
            return None
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
            raise ValueError('Warna harus berupa #RRGGBB')
        if info.field_name == 'color_primary' and contrast(value) < 4.5:
            raise ValueError('Warna utama harus memiliki kontras minimal 4.5:1 terhadap putih')
        return value.upper()


def public_response(request, response, db):
    value = current(db)
    etag = '"' + hashlib.sha256(repr(sorted(value.items())).encode()).hexdigest()[:24] + '"'
    response.headers['Cache-Control'] = 'public, max-age=30, must-revalidate'
    response.headers['ETag'] = etag
    if request.headers.get('if-none-match') == etag:
        response.status_code = 304
        return None
    return value


@router.get('')
def get_branding(request: Request, response: Response, db: Session = Depends(get_db)):
    return public_response(request, response, db)


@router.put('')
def put_branding(body: BrandingInput, u: User = Depends(require('admin')),
                 db: Session = Depends(get_db)):
    before = current(db)
    row = ensure_row(db)
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    row.updated_by, row.updated_at = u.id, now()
    after = current(db)
    db.add(AuditLog(user_id=u.id, action='branding_update', target='app_branding',
                    detail={'before': {k: before[k] for k in FIELDS},
                            'after': {k: after[k] for k in FIELDS}}))
    db.commit()
    return current(db)


def icon_response(kind: str, db: Session, request: Request, response: Response):
    b = current(db)
    path = image_path(kind)
    custom = b['has_logo' if kind == 'logo' else 'has_favicon'] and path.is_file()
    version = b[f'{kind}_version']
    headers = {'X-Content-Type-Options': 'nosniff',
               'Cache-Control': 'public, max-age=31536000, immutable' if request.query_params.get('v') == str(version)
                                else 'public, max-age=60'}
    return FileResponse(path if custom else ICON, media_type='image/png' if custom else 'image/svg+xml', headers=headers)


@router.get('/logo')
def logo(request: Request, response: Response, db: Session = Depends(get_db)):
    return icon_response('logo', db, request, response)


@router.get('/favicon')
def favicon(request: Request, response: Response, db: Session = Depends(get_db)):
    return icon_response('favicon', db, request, response)


def _change_image(kind, action, user, db):
    before = current(db)
    row = ensure_row(db)
    setattr(row, f'{kind}_ext', 'png' if action == 'upload' else None)
    setattr(row, f'{kind}_version', getattr(row, f'{kind}_version') + 1)
    row.updated_by, row.updated_at = user.id, now()
    db.add(AuditLog(user_id=user.id, action=f'branding_{kind}_{action}', target=kind,
                    detail={'before_version': before[f'{kind}_version'],
                            'after_version': getattr(row, f'{kind}_version')}))
    db.commit()
    return current(db)


@router.post('/reset')
def reset(user: User = Depends(require('admin')), db: Session = Depends(get_db)):
    before = current(db)
    row = ensure_row(db)
    for field in FIELDS:
        setattr(row, field, None)
    for kind in ('logo', 'favicon'):
        setattr(row, f'{kind}_ext', None)
        setattr(row, f'{kind}_version', getattr(row, f'{kind}_version') + 1)
    row.updated_by, row.updated_at = user.id, now()
    db.add(AuditLog(user_id=user.id, action='branding_reset', target='app_branding',
                    detail={'before': before, 'after': current(db)}))
    db.commit()
    for kind in ('logo', 'favicon'):
        image_path(kind).unlink(missing_ok=True)
    return current(db)


@router.post('/{kind}')
async def upload(kind: str, file: UploadFile = File(...), user: User = Depends(require('admin')),
                 db: Session = Depends(get_db)):
    if kind not in ('logo', 'favicon'):
        raise HTTPException(404, 'Jenis gambar tidak tersedia')
    size = 512 * 1024 if kind == 'logo' else 128 * 1024
    data = await file.read(size + 1)
    image = decode_image(data, kind)
    path = image_path(kind)
    previous = path.read_bytes() if path.exists() else None
    save_atomically(kind, image)
    try:
        return _change_image(kind, 'upload', user, db)
    except Exception:
        db.rollback()
        if previous is None:
            path.unlink(missing_ok=True)
        else:
            save_atomically(kind, previous)
        raise


@router.delete('/{kind}')
def delete(kind: str, user: User = Depends(require('admin')),
           db: Session = Depends(get_db)):
    if kind not in ('logo', 'favicon'):
        raise HTTPException(404, 'Jenis gambar tidak tersedia')
    result = _change_image(kind, 'delete', user, db)
    image_path(kind).unlink(missing_ok=True)
    return result


