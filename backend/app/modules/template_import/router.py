"""Download, preview and all-or-nothing commit for BerauLoad-generated XLSX."""
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from uuid import uuid4
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ...db import get_db, User, ImportBatch
from ...security import current_user, require
from ..org_units.context import UnitContext, unit_context, require_action
from . import repository
from .migrations import run as migrate
from .service import plan, write, MODES
from .validator import parse, TemplateInvalid, MAX_UPLOAD
from .workbook import build

router = APIRouter(prefix='/api/template-import', tags=['Template Import'])
UPLOAD_DIR = Path(os.getenv('UPLOAD_DIR', '/data/uploads'))
STAGING = UPLOAD_DIR / 'staging' / 'template_import'


def _period(start, end):
    if start > end or (end-start).days >= 92:
        raise HTTPException(422, 'Rentang tanggal maksimal 92 hari')


def _validate(contents, db, unit_id, unit):
    try:
        return parse(contents, db, unit_id, unit)
    except TemplateInvalid as exc:
        raise HTTPException(422, {'message': 'File template ditolak',
                                  'errors': exc.errors}) from exc


def _staging_path(token, ext):
    return STAGING / (token + ext)


def _load_stage(token, user_id, unit_id):
    meta_file, source = _staging_path(token, '.json'), _staging_path(token, '.xlsx')
    if not meta_file.is_file() or not source.is_file():
        raise HTTPException(404, 'Token pratinjau tidak ditemukan')
    try:
        meta = json.loads(meta_file.read_text(encoding='utf8'))
        if meta['user_id'] != user_id or meta['unit_id'] != unit_id:
            raise HTTPException(403, 'Token bukan milik pengguna/unit ini')
        created = datetime.fromisoformat(meta['created_at'])
        if datetime.now(timezone.utc) - created > timedelta(hours=1):
            raise HTTPException(410, 'Token kedaluwarsa; pratinjau ulang')
        contents = source.read_bytes()
        if len(contents) > MAX_UPLOAD or hashlib.sha256(contents).hexdigest() != meta['sha256']:
            raise HTTPException(409, 'File staging berubah')
    except (KeyError, ValueError, OSError) as exc:
        raise HTTPException(409, 'Metadata staging tidak sah') from exc
    return meta, contents


def _stream_file(path):
    try:
        with open(path, 'rb') as src:
            while chunk := src.read(65536):
                yield chunk
    finally:
        Path(path).unlink(missing_ok=True)


@router.get('/config')
def config(ctx: UnitContext = Depends(unit_context('read')), db: Session = Depends(get_db)):
    unit = ctx.unit
    tabs = repository.eligible_tabs(db, unit.id)
    return {'unit': {'id': unit.id, 'code': unit.code, 'name': unit.name},
            'tabs': [{'code': t.code, 'name': t.name,
                      'parameters': len(metrics)} for t, metrics in tabs]}


@router.get('/template')
def template(start: date, end: date, tabs: str | None = None,
             ctx: UnitContext = Depends(unit_context('read')),
             db: Session = Depends(get_db)):
    if not ctx.superadmin and not ctx.roles.intersection(('admin', 'operator', 'verifier')):
        raise HTTPException(403, 'Peran ini tidak dapat mengunduh template input')
    if ctx.unit.level == 'up3':
        raise HTTPException(422, 'Pilih ULP atau KP untuk mengisi data')
    _period(start, end)
    unit = ctx.unit
    names = [s.strip() for s in tabs.split(',')] if tabs else None
    if names is not None and (not all(names) or len(names) != len(set(names))):
        raise HTTPException(422, 'Tab yang dipilih tidak valid')
    try:
        path = build(db, unit.id, unit, start, end, names)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    filename = f'BerauLoad_Template_{unit.code}_{start}_{end}.xlsx'
    return StreamingResponse(_stream_file(path), media_type=(
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
        headers={'Content-Disposition': f'attachment; filename="{filename}"'})


@router.post('/preview')
async def preview(file: UploadFile = File(...), mode: str = Form('fill_empty'),
                  ctx: UnitContext = Depends(unit_context('write_data')),
                  db: Session = Depends(get_db)):
    require_action(ctx, 'operator')
    if mode not in MODES:
        raise HTTPException(422, 'Mode import harus fill_empty atau new_hours')
    if not file.filename or not file.filename.lower().endswith('.xlsx'):
        raise HTTPException(422, 'Hanya file .xlsx yang diperbolehkan')
    contents = await file.read(MAX_UPLOAD+1)
    if len(contents) > MAX_UPLOAD:
        raise HTTPException(413, 'Maksimum file 15 MB')
    unit = ctx.unit
    parsed = _validate(contents, db, unit.id, unit)
    digest = hashlib.sha256(contents).hexdigest()
    if repository.imported_already(db, unit.id, digest):
        raise HTTPException(409, 'File identik sudah pernah diimport untuk unit ini')
    preview_result = plan(db, unit.id, parsed, mode)
    token = str(uuid4())
    STAGING.mkdir(parents=True, exist_ok=True)
    meta = {'user_id': ctx.actor.id, 'unit_id': unit.id, 'mode': mode,
            'filename': Path(file.filename).name[:250], 'sha256': digest,
            'created_at': datetime.now(timezone.utc).isoformat()}
    _staging_path(token, '.xlsx').write_bytes(contents)
    _staging_path(token, '.json').write_text(json.dumps(meta), encoding='utf8')
    os.chmod(_staging_path(token, '.xlsx'), 0o600)
    os.chmod(_staging_path(token, '.json'), 0o600)
    return {'token': token, 'unit_code': unit.code, 'mode': mode,
            'period': {'start': parsed['start'].isoformat(),
                       'end': parsed['end'].isoformat()},
            'parameter_codes': parsed['parameter_codes'],
            'hours_to_write': preview_result['hours_to_write'],
            'values_found': preview_result['values_found'],
            'counts': preview_result['totals'],
            'by_parameter': preview_result['by_parameter'],
            'differences': preview_result['differences'], 'errors': []}


class CommitBody(BaseModel):
    token: str = Field(pattern=r'^[a-f0-9-]{36}$')


@router.post('/commit')
def commit(body: CommitBody,
           ctx: UnitContext = Depends(unit_context('write_data')),
           db: Session = Depends(get_db)):
    require_action(ctx, 'operator')
    unit = ctx.unit
    meta, contents = _load_stage(body.token, ctx.actor.id, unit.id)
    parsed = _validate(contents, db, unit.id, unit)
    batch_id = str(uuid4())
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    archive = UPLOAD_DIR / (batch_id + '.xlsx')
    # Write archive first: a database commit can never refer to a missing file.
    archive_created = False
    try:
        with open(archive, 'xb') as dest:
            archive_created = True
            os.chmod(archive, 0o600)
            dest.write(contents)
        result = write(db, unit.id, parsed, meta['mode'], ctx.actor, batch_id,
                       meta['filename'], meta['sha256'])
        db.commit()
    except (FileExistsError, IntegrityError) as exc:
        db.rollback()
        if archive_created:
            archive.unlink(missing_ok=True)
        raise HTTPException(409, 'File identik atau import bersamaan terdeteksi') from exc
    except Exception:
        db.rollback()
        if archive_created:
            archive.unlink(missing_ok=True)
        raise
    _staging_path(body.token, '.json').unlink(missing_ok=True)
    _staging_path(body.token, '.xlsx').unlink(missing_ok=True)
    from ..performance.cache import clear_reading_cache
    clear_reading_cache()
    return result


@router.get('/history')
def history(ctx: UnitContext = Depends(unit_context('read')), db: Session = Depends(get_db)):
    rows = db.query(ImportBatch).filter_by(unit_id=ctx.id).order_by(ImportBatch.created_at.desc()).limit(150).all()
    return [{'id': r.id, 'filename': r.filename, 'unit_id': r.unit_id,
             'kind': r.kind or 'legacy_excel', 'year': r.year, 'month': r.month,
             'readings_created': r.readings_created,
             'hours_created': r.hours_created,
             'created_at': r.created_at.isoformat() if r.created_at else None}
            for r in rows]
