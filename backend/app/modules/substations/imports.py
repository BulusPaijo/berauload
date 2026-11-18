"""Preview-first Excel/CSV import, no database changes before confirmation."""
from datetime import date
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from ...db import get_db
from ..org_units.context import UnitContext, unit_context
from .common import (master_context, audit, check_code, check_master, data_units, ensure_data_unit, ensure_owner,
                     family_code_taken, feeder_units, require_admin, require_master_manager, ulp_of)
from .models import (Substation, SubstationFeeder, SubstationMeasurement,
                     SubstationValue)
from .schemas import ImportApply, MasterForm, MasterPatch, VisitForm
from .master import update_master
from .visits_service import save_visit
from .imports_service import (load_stage, master_preview, master_template,
    measurement_preview, measurement_template, parse_uploaded, stage_preview)

router = APIRouter(prefix='/api/substations', tags=['Substation XLSX/CSV'])
MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def xlsx(blob, filename):
    return Response(content=blob, media_type=MIME,
       headers={'Content-Disposition': f'attachment; filename="{filename}"',
                'X-Content-Type-Options': 'nosniff'})


async def preview_file(file, db, ctx, kind):
    data = await file.read(4 * 1024 * 1024 + 1)
    rows = parse_uploaded(data, file.filename or '')
    units = data_units(db, ctx)
    parsed = (master_preview(db, units, rows, feeder_units(db, ctx.id)) if kind == 'master'
              else measurement_preview(db, units, rows))
    token = stage_preview(ctx.actor.id, ctx.id, kind, parsed)
    return {'token': token, **parsed}


@router.get('/master/template')
def get_master_template(ctx: UnitContext = Depends(unit_context('read')),
                        db: Session = Depends(get_db)):
    if ctx.unit.level == 'up3':
        raise HTTPException(422, 'Pilih ULP atau KP')
    units = data_units(db, ctx) or [ctx.id]
    return xlsx(master_template(db, units, feeder_units(db, ctx.id)), 'master_gardu.xlsx')


@router.post('/master/import/preview')
async def preview_master(file: UploadFile = File(...),
                         ctx: UnitContext = Depends(master_context()),
                         db: Session = Depends(get_db)):
    return await preview_file(file, db, ctx, 'master')


@router.post('/master/import/apply')
def apply_master(body: ImportApply,
                 ctx: UnitContext = Depends(master_context()),
                 db: Session = Depends(get_db)):
    preview, path = load_stage(body.token, ctx.actor.id, ctx.id, 'master')
    family = data_units(db, ctx)
    feeder_owner = feeder_units(db, ctx.id)[-1]   # feeders live on the ULP
    missing = preview['new_feeders']
    if missing and not body.create_feeders:
        raise HTTPException(422, {'new_feeders': missing, 'reason': 'Konfirmasi pembuatan penyulang baru'})
    feeders = {f.code: f.id for f in db.query(SubstationFeeder).filter(
        SubstationFeeder.unit_id.in_(feeder_units(db, ctx.id)))}
    for code in missing:
        check_code(code)
        row = SubstationFeeder(unit_id=feeder_owner, code=code, name=code)
        db.add(row); db.flush(); feeders[code] = row.id
        audit(db, ctx, 'substation_feeder_create_import', code)
    from .calculation_service import prepare
    calc_prepared = prepare(db)
    results = []
    for item in preview['rows']:
        if item['errors']:
            results.append({'row': item['row'], 'status': 'error', 'reason': item['errors']})
            continue
        data = dict(item['values'])
        feeder_code = data.pop('feeder_code', '')
        if feeder_code:
            data['feeder_id'] = feeders[feeder_code]
        try:
            with db.begin_nested():
                existing = db.query(Substation).filter(Substation.unit_id.in_(family),
                                                       Substation.code == data['code']).first()
                if existing:
                    if not body.update_existing:
                        results.append({'row': item['row'], 'status': 'skipped'})
                        continue
                    patch = MasterPatch(**{k:v for k,v in data.items() if k!='code'})
                    changed = update_master(db, ctx, existing,
                                 patch.model_dump(exclude_unset=True))
                    status = 'updated' if changed else 'unchanged'
                else:
                    form = MasterForm(**data)
                    values = form.model_dump()
                    target = values.pop('unit_id') or ctx.id
                    ensure_data_unit(db, ctx, target)
                    if family_code_taken(db, target, values['code']):
                        raise HTTPException(409, 'Kode gardu sudah dipakai')
                    row = Substation(unit_id=target, **check_master(db, target, values),
                         created_by=ctx.actor.id, updated_by=ctx.actor.id)
                    db.add(row); db.flush()
                    audit(db, ctx, 'substation_master_create_import', row.code)
                    status = 'created'
            results.append({'row': item['row'], 'status': status})
        except (HTTPException, ValueError) as exc:
            results.append({'row': item['row'], 'status': 'error', 'reason': str(exc)})
    db.commit(); path.unlink(missing_ok=True)
    return {'results': results}


@router.get('/measurements/template')
def get_visit_template(feeder_id: int | None = None, day: date | None = None, session: str | None = None,
                       ctx: UnitContext = Depends(unit_context('read')),
                       db: Session = Depends(get_db)):
    if ctx.unit.level == 'up3':
        raise HTTPException(422, 'Pilih ULP atau KP')
    return xlsx(measurement_template(db, data_units(db, ctx), feeder_id, day, session), 'pengukuran_gardu.xlsx')


@router.post('/measurements/import/preview')
async def preview_visits(file: UploadFile = File(...),
                         ctx: UnitContext = Depends(unit_context('write_data')),
                         db: Session = Depends(get_db)):
    return await preview_file(file, db, ctx, 'measurements')


@router.post('/measurements/import/apply')
def apply_visits(body: ImportApply,
                 ctx: UnitContext = Depends(unit_context('write_data')),
                 db: Session = Depends(get_db)):
    preview, path = load_stage(body.token, ctx.actor.id, ctx.id, 'measurements')
    from .calculation_service import prepare
    calc_prepared = prepare(db)
    results = []
    for item in preview['rows']:
        if item['errors']:
            results.append({'row': item['row'], 'status': 'error', 'reason': item['errors']})
            continue
        try:
            with db.begin_nested():
                data = item['values']
                existing = db.query(SubstationMeasurement).filter_by(
                    substation_id=data['substation_id'], measured_on=date.fromisoformat(
                    data['measured_on']), session=data['session']).first()
                if existing and existing.state == 'verified':
                    raise HTTPException(409, 'Verified terkunci')
                if existing:
                    data['revision'] = existing.revision
                result = save_visit(db, ctx, VisitForm(**data),
                                    fill_empty=body.mode == 'fill_empty', calc_prepared=calc_prepared)
            results.append({'row': item['row'], 'status': result['status']})
        except (HTTPException, ValueError) as exc:
            results.append({'row': item['row'], 'status': 'error', 'reason': str(exc)})
    db.commit(); path.unlink(missing_ok=True)
    return {'results': results}
