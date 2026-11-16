"""Manual hourly input with scoped metrics and global hour slots."""
from datetime import date, datetime, time, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from ...db import Asset, Metric, Reading, HourRecord, AuditLog, get_db
from ...catalog import CODE_MAP, calculate
from ..formulas.service import calculate_custom, active_plan
from ..formulas.engine import parse_formula
from ..unit_references.recalculation import recalculate
from ..performance.cache import clear_reading_cache
from ..org_units.context import UnitContext, unit_context, require_action, audit_details
from ..org_units.repository import home_unit
from .service import day_status
from .locking import lock_hour
from .conflicts import check_base, equal_value, last_editor
router = APIRouter(prefix='/api', tags=['Records'])
TZ=ZoneInfo('Asia/Makassar')

def audit(db,u,action,target,detail):
    db.add(AuditLog(user_id=u.id,action=action,target=target,detail=detail))


def formula_plan(db, unit_id):
    """Never evaluate a formula whose output/input belongs to another unit."""
    plan=active_plan(db)
    owners={m.code:m.unit_id for m in db.query(Metric).all()}
    return [(definition, metric) for definition,metric in plan
            if metric.unit_id==unit_id and all(
                owners.get(ref)==unit_id for ref in parse_formula(definition.expression)[1])]

class HourPayload(BaseModel):
    values:dict[str,float|None]
    note:str|None=None
    base:dict[str,float|None]|None=None
    overrides:list[str]|None=None
    @field_validator('values')
    @classmethod
    def valid_values(cls,v):
        if len(v)>110: raise ValueError('Terlalu banyak parameter')
        for key,value in v.items():
            if not key or len(key)>90 or not all(c.isalnum() or c=='_' for c in key): raise ValueError('Kode parameter tidak valid')
            if value is not None and (not -1e9<value<1e9): raise ValueError('Nilai di luar batas teknis sistem')
        return v

    @field_validator('base')
    @classmethod
    def valid_base(cls, v):
        if v is not None:
            if len(v) > 110:
                raise ValueError('Terlalu banyak nilai dasar')
            for code, value in v.items():
                if not code or len(code) > 90 or not all(
                        c.isalnum() or c == '_' for c in code):
                    raise ValueError('Kode dasar tidak valid')
                if value is not None and (not -1e9 < value < 1e9):
                    raise ValueError('Nilai dasar di luar batas sistem')
        return v

def save_readings(db,day,hour,values,source,unit_id,by=None,batch_id=None,overwrite=True):
    record=db.query(HourRecord).filter_by(day=day,hour=hour).first()
    if not record and db.bind.dialect.name == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
        ts=datetime.combine(day,time(hour=hour),tzinfo=TZ).astimezone(timezone.utc)
        db.execute(insert(HourRecord).values(day=day,hour=hour,timestamp_utc=ts,
                   entered_by=by).on_conflict_do_nothing(
                   index_elements=['day','hour']))
        record=db.query(HourRecord).filter_by(day=day,hour=hour).first()
    if not record:
        ts=datetime.combine(day,time(hour=hour),tzinfo=TZ).astimezone(timezone.utc)
        record=HourRecord(day=day,hour=hour,timestamp_utc=ts,entered_by=by)
        db.add(record);db.flush()
    mid={m.code:m.id for m in db.query(Metric).filter(Metric.unit_id==unit_id,Metric.code.in_(list(values))).all()}
    old={r.metric_id:r for r in db.query(Reading).filter(
        Reading.hour_id==record.id, Reading.metric_id.in_(list(mid.values()))).all()}
    for code,value in values.items():
        if code not in mid:continue
        ident=mid[code]
        if value is None:
            if overwrite and ident in old:db.delete(old[ident])
        elif ident in old:
            if overwrite and old[ident].value != Decimal(str(value)):
                old[ident].value=Decimal(str(value));old[ident].source=source
                old[ident].import_batch_id=batch_id
        else:
            db.add(Reading(hour_id=record.id,metric_id=ident,value=Decimal(str(value)),
                           source=source,import_batch_id=batch_id))
    return record

def hour_values(db, day, hour, unit_id):
    """Only the selected hour; never reload all 24 hours for a single edit."""
    rows = (db.query(Metric.code, Reading.value)
            .join(Reading, Reading.metric_id == Metric.id)
            .join(HourRecord, HourRecord.id == Reading.hour_id)
            .filter(HourRecord.day == day, HourRecord.hour == hour,
                    Metric.unit_id == unit_id).all())
    return {code: float(value) for code, value in rows}


def derived_values(db, ctx, previous, body_values):
    input_codes = {m.code for m in db.query(Metric).filter_by(
        input_mode='input', active=True, unit_id=ctx.id).all()}
    for code in body_values:
        if code not in input_codes:
            raise HTTPException(422, 'Parameter tidak aktif atau tidak dapat diinput: '+code)
    combined_inputs = {k:v for k,v in previous.items() if k in input_codes}
    combined_inputs.update(body_values)
    source_only = {k:v for k,v in previous.items()
                   if ctx.unit.legacy_home and k in CODE_MAP
                   and CODE_MAP[k][4] == 'imported'}
    power_keys = {'pltu_lati_cb33_kw','pltu_lati_cb31_kw','sewa_tama_1_kw',
       'sewa_tama_2_kw','pltd_kw','pltu_berau_og3_kw','pltu_berau_og4_kw',
       'beban_suaran_kw','pltd_berau_kw','incoming_gi_kw'}
    changed_power = ctx.unit.legacy_home and any(
        k in power_keys and not equal_value(previous.get(k), v)
        for k,v in body_values.items())
    computed = calculate({k:v for k,v in {**source_only,**combined_inputs}.items()
                          if v is not None}) if changed_power else {}
    combined = {**combined_inputs, **computed}
    for code, meta in CODE_MAP.items():
        if (ctx.unit.legacy_home and meta[4] == 'computed'
                and code not in computed and code in previous):
            combined[code] = previous[code]
    custom, warnings = calculate_custom(db, {**previous, **source_only, **combined},
                                         plan=formula_plan(db, ctx.id))
    return {**computed, **custom}, warnings


@router.put('/records/{day}/{hour}')
def put_hour(day:date,hour:int,body:HourPayload,
             ctx:UnitContext=Depends(unit_context('write_data')),
             db:Session=Depends(get_db)):
    require_action(ctx, 'operator')
    if not 0 <= hour <= 23:
        raise HTTPException(422, 'Jam harus 0-23')
    # PostgreSQL transaction lock protects read->compare->write for this unit/hour.
    lock_hour(db, ctx.id, day, hour)
    if day_status(db, day, ctx.id) != 'draft':
        raise HTTPException(409, 'Hari terkunci. Admin harus membuka kembali.')
    previous = hour_values(db, day, hour, ctx.id)
    changes = {k:v for k,v in body.values.items()
               if not equal_value(previous.get(k), v)}
    # Validate all codes even for a no-op; do not allow a silent invalid edit.
    allowed = {m.code for m in db.query(Metric).filter_by(
        input_mode='input', active=True, unit_id=ctx.id).all()}
    if any(code not in allowed for code in body.values):
        raise HTTPException(422, 'Parameter tidak aktif atau tidak dapat diinput')
    check_base(db, changes, body.base, previous, day, hour, ctx.id)
    if not changes:
        return {'ok': True, 'unchanged': True, 'computed': {},
                'formula_warnings': []}
    if not previous and not any(v is not None for v in changes.values()):
        raise HTTPException(422, 'Isi minimal satu pengukuran sebelum menyimpan')
    derived, warnings = derived_values(db, ctx, previous, changes)
    updates = {**changes, **{k:v for k,v in derived.items()
                             if not equal_value(previous.get(k), v)}}
    override_info = {}
    for code in (body.overrides or []):
        if code not in changes:
            raise HTTPException(422, 'Override hanya untuk nilai yang diubah')
        who, when = last_editor(db, code, day, hour, ctx.id)
        override_info[code] = {'server_old': previous.get(code),
                               'last_editor': who, 'last_edited_at': when}
    save_readings(db, day, hour, updates, 'manual', ctx.id, ctx.actor.id)
    recalculate(db, day, hour, ctx.id, set(updates))
    audit(db, ctx.actor, 'hour_save', f'{day} {hour:02d}:00',
          audit_details(ctx, 'operator', changes={k:{'old':previous.get(k),
          'new':v} for k,v in changes.items()}, note=body.note,
          overrides=override_info))
    db.commit()
    clear_reading_cache()
    return {'ok': True, 'unchanged': False, 'computed': derived,
            'formula_warnings': warnings}
