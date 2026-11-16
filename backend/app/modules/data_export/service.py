"""Validated export specs and safe presentation; never modifies readings."""
from __future__ import annotations
import re
from datetime import date
from itertools import groupby
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from ...db import HourRecord, Metric, Reading
from ..org_units.models import UnitDayState
from ..org_units.references import unit_ids
from ..units.models import UnitDefinition
from ..units.service import convert, profile

META = {'tanggal': 'Tanggal (WITA)', 'jam': 'Jam (WITA)', 'status': 'Status Hari'}
MAX_COLUMNS = 45
MAX_ROWS = 120_000
MAX_DAYS = 3660
CODE = re.compile(r'^[a-z][a-z0-9_]*$')


def validate_spec(db: Session, spec: dict, start: date, end: date, unit_id=None):
    if end < start or start.year < 2000 or end.year > 2100 or (end-start).days > MAX_DAYS:
        raise HTTPException(422, 'Periode export tidak valid atau melebihi 10 tahun')
    grain, agg = spec['granularity'], spec['aggregation']
    if grain not in {'hour', 'day', 'month', 'year'} or agg not in {'avg', 'min', 'max'}:
        raise HTTPException(422, 'Resolusi atau agregasi tidak dikenal')
    cols = spec['columns']
    if not 2 <= len(cols) <= MAX_COLUMNS or len(cols) != len(set(cols)):
        raise HTTPException(422, 'Pilih 2–45 kolom berbeda')
    if grain != 'hour' and any(code in {'jam', 'status'} for code in cols):
        raise HTTPException(422, 'Jam dan status hanya tersedia untuk pengukuran per jam')
    if 'tanggal' not in cols or not any(c not in META for c in cols):
        raise HTTPException(422, 'Tanggal dan minimal satu parameter wajib dipilih')
    metrics = {m.code: m for m in db.query(Metric).filter(
        Metric.code.in_([c for c in cols if c not in META]),Metric.unit_id.in_(unit_ids(db, unit_id, active_only=False)) if unit_id is not None else True).all()}
    if any(code not in META and (not CODE.fullmatch(code) or code not in metrics)
           for code in cols):
        raise HTTPException(422, 'Parameter tidak ditemukan')
    overrides = spec.get('unit_overrides') or {}
    titles = spec.get('headers') or {}
    if not set(overrides).issubset(metrics) or not set(titles).issubset(cols):
        raise HTTPException(422, 'Konfigurasi judul atau satuan tidak sesuai kolom')
    units = profile(db.query(UnitDefinition).all())
    for code, unit in overrides.items():
        if not unit or unit not in units or metrics[code].unit not in units or (
            units[unit].dimension != units[metrics[code].unit].dimension):
            raise HTTPException(422, f'Satuan konversi tidak kompatibel: {code}')
    if any(len(name) > 90 or not name.strip() for name in titles.values()):
        raise HTTPException(422, 'Judul kolom harus berisi 1–90 karakter')
    estimated = ((end-start).days+1)*24 if grain == 'hour' else (
        (end-start).days+1 if grain == 'day' else 12*((end.year-start.year)+1))
    if estimated > MAX_ROWS:
        raise HTTPException(422, 'Terlalu banyak baris; pecah export menjadi beberapa periode')
    return metrics, units


def headers(spec: dict, metrics: dict) -> list[str]:
    overrides = spec.get('unit_overrides') or {}
    custom = spec.get('headers') or {}
    return [custom.get(code) or META.get(code) or (
        f'{metrics[code].name} ({overrides.get(code, metrics[code].unit)})')
        for code in spec['columns']]


def _format_value(value, code, metrics, units, spec):
    if value is None:
        return None
    overrides = spec.get('unit_overrides') or {}
    target = overrides.get(code)
    if target and target != metrics[code].unit:
        return convert(float(value), units[metrics[code].unit], units[target])
    return float(value)


def _hourly(db: Session, codes: list, start: date, end: date, unit_id=None):
    query = (db.query(HourRecord.day, HourRecord.hour, UnitDayState.status,
                      Metric.code, Reading.value)
             .join(Reading, Reading.hour_id == HourRecord.id)
             .join(Metric, Metric.id == Reading.metric_id)
             .outerjoin(UnitDayState, (UnitDayState.day == HourRecord.day) & (UnitDayState.unit_id == unit_id))
             .filter(HourRecord.day >= start, HourRecord.day <= end, Metric.code.in_(codes), Metric.unit_id.in_(unit_ids(db, unit_id, active_only=False)) if unit_id is not None else True)
             .order_by(HourRecord.day, HourRecord.hour, Metric.code))
    for (day, hour), group in groupby(query.yield_per(1000), lambda r: (r[0], r[1])):
        rows = list(group)
        yield {'tanggal': day.isoformat(), 'jam': f'{hour:02d}:00',
               'status': rows[0][2] or 'draft',
               **{code: value for _, _, _, code, value in rows}}


def _aggregated(db: Session, codes: list, start: date, end: date, grain: str, agg: str, unit_id=None):
    if grain == 'day':
        parts = [HourRecord.day]
    elif grain == 'month':
        parts = [func.extract('year', HourRecord.day), func.extract('month', HourRecord.day)]
    else:
        parts = [func.extract('year', HourRecord.day)]
    operation = {'avg': func.avg, 'min': func.min, 'max': func.max}[agg]
    query = (db.query(*parts, Metric.code, operation(Reading.value))
             .join(Reading, Reading.hour_id == HourRecord.id)
             .join(Metric, Metric.id == Reading.metric_id)
             .filter(HourRecord.day >= start, HourRecord.day <= end, Metric.code.in_(codes),Metric.unit_id.in_(unit_ids(db, unit_id, active_only=False)) if unit_id is not None else True)
             .group_by(*parts, Metric.code).order_by(*parts, Metric.code))
    n = len(parts)
    for key, group in groupby(query.yield_per(1000), lambda r: tuple(r[:n])):
        period = (key[0].isoformat() if grain == 'day' else
                  f'{int(key[0])}-{int(key[1]):02d}' if grain == 'month' else str(int(key[0])))
        yield {'tanggal': period, **{r[n]: r[n+1] for r in group}}


def export_rows(db: Session, spec: dict, start: date, end: date,
                metrics: dict, units: dict, unit_id=None):
    codes = [c for c in spec['columns'] if c not in META]
    source = (_hourly(db, codes, start, end, unit_id) if spec['granularity'] == 'hour' else
              _aggregated(db, codes, start, end, spec['granularity'], spec['aggregation'],unit_id))
    for row in source:
        yield [row.get(c) if c in META else _format_value(row.get(c), c, metrics, units, spec)
               for c in spec['columns']]


def safe_spreadsheet_text(value):
    """Prevent formulas when opening untrusted labels in spreadsheet software."""
    if not isinstance(value, str):
        return value
    if value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')):
        return "'" + value
    return value
