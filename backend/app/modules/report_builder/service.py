"""Pure report configuration validation and read-only data projection."""
from __future__ import annotations
from collections import defaultdict
from datetime import date, timedelta
import re
from fastapi import HTTPException
from sqlalchemy.orm import Session
from ..org_units.references import unit_ids, status_summary
from ...db import HourRecord, Metric, Reading

KINDS = {'heading', 'text', 'stat', 'chart', 'table'}
AGGS = {'avg', 'min', 'peak'}
GRAINS = {'hour', 'day', 'month'}
CODE = re.compile(r'^[a-z][a-z0-9_]{1,88}$')
MAX_BLOCKS = 16
MAX_DAYS = 366
MAX_TEMPLATES = 30


def validate_blocks(blocks: list[dict], known: dict[str, str]) -> list[dict]:
    if not 1 <= len(blocks) <= MAX_BLOCKS:
        raise HTTPException(422, 'Laporan harus memuat 1–16 blok')
    ids = set()
    for block in blocks:
        if block['id'] in ids:
            raise HTTPException(422, 'ID blok duplikat')
        ids.add(block['id'])
        if block['kind'] not in KINDS:
            raise HTTPException(422, 'Jenis blok laporan tidak dikenal')
        if block['kind'] in {'heading', 'text'}:
            if block['metric_codes']:
                raise HTTPException(422, 'Blok teks tidak memiliki parameter')
        else:
            codes = block['metric_codes']
            max_codes = 1 if block['kind'] == 'stat' else 2
            if not 1 <= len(codes) <= max_codes or len(set(codes)) != len(codes):
                raise HTTPException(422, 'Jumlah parameter blok tidak valid')
            if any(not CODE.fullmatch(c) or c not in known for c in codes):
                raise HTTPException(422, 'Parameter laporan tidak tersedia')
            if len({known[c] for c in codes}) != 1:
                raise HTTPException(422, 'Satuan berbeda tidak boleh dicampur dalam satu grafik')
        if block['aggregation'] not in AGGS or block['granularity'] not in GRAINS:
            raise HTTPException(422, 'Agregasi atau resolusi tidak valid')
    return blocks


def validate_period(start: date, end: date, blocks: list[dict]):
    if end < start or start.year < 2000 or (end - start).days > MAX_DAYS:
        raise HTTPException(422, 'Rentang laporan maksimal 367 hari')
    if (end - start).days > 30 and any(b['granularity'] == 'hour' for b in blocks
                                       if b['kind'] not in {'heading', 'text'}):
        raise HTTPException(422, 'Grafik per jam maksimal 31 hari')


def _key(day, hour, grain):
    if grain == 'hour':
        return f'{day.isoformat()} {hour:02d}:00'
    if grain == 'month':
        return day.strftime('%Y-%m')
    return day.isoformat()


def _agg(values: list[float], method: str):
    if not values:
        return None
    if method == 'min':
        return min(values)
    if method == 'peak':
        return max(values)
    return sum(values) / len(values)


def _read_values(db: Session, codes: list[str], start: date, end: date, unit_id=None):
    rows = (db.query(HourRecord.day, HourRecord.hour, Metric.code, Reading.value)
            .join(Reading, Reading.hour_id == HourRecord.id)
            .join(Metric, Metric.id == Reading.metric_id)
            .filter(HourRecord.day >= start, HourRecord.day <= end,
                    Metric.code.in_(codes), Metric.unit_id.in_(unit_ids(db, unit_id, active_only=False)) if unit_id is not None else True)
            .order_by(HourRecord.day, HourRecord.hour).all())
    values = defaultdict(dict)
    for day, hour, code, value in rows:
        values[(day, hour)][code] = float(value)
    return values


def _period_keys(start: date, end: date, grain: str):
    current = start
    seen = set()
    while current <= end:
        if grain == 'hour':
            for hour in range(24):
                yield _key(current, hour, grain)
        else:
            key = _key(current, 0, grain)
            if key not in seen:
                yield key
                seen.add(key)
        current += timedelta(days=1)


def _series(values, codes: list[str], grain: str, method: str, start: date, end: date):
    grouped = defaultdict(lambda: defaultdict(list))
    for (day, hour), recorded in values.items():
        # Paired measurements must use the same hour in a comparison.
        if len(codes) == 2 and not all(c in recorded for c in codes):
            continue
        key = _key(day, hour, grain)
        for code in codes:
            if code in recorded:
                grouped[key][code].append(recorded[code])
    return [{'period': p, **{c: _agg(by_code.get(c, []), method) for c in codes},
             'paired_count': len(next(iter(by_code.values()), [])) if len(codes) == 2 else None}
            for p in _period_keys(start, end, grain)
            for by_code in [grouped.get(p, {})]]


def render_blocks(db: Session, blocks: list[dict], start: date, end: date, unit_id=None):
    validate_period(start, end, blocks)
    needed = sorted(set(c for b in blocks for c in b['metric_codes']))
    metrics = {m.code: m for m in db.query(Metric).filter(Metric.code.in_(needed),Metric.unit_id.in_(unit_ids(db, unit_id, active_only=False)) if unit_id is not None else True).all()}
    validate_blocks(blocks, {code: m.unit for code, m in metrics.items()})
    recorded = _read_values(db, needed, start, end, unit_id)
    items = []
    for b in blocks:
        info = {'id': b['id'], 'kind': b['kind'], 'title': b['title'],
                'text': b['text'], 'unit': metrics[b['metric_codes'][0]].unit
                if b['metric_codes'] else '', 'metric_codes': b['metric_codes']}
        if b['kind'] == 'stat':
            code = b['metric_codes'][0]
            all_values = [v[code] for v in recorded.values() if code in v]
            info.update(value=_agg(all_values, b['aggregation']), count=len(all_values))
        elif b['kind'] in {'chart', 'table'}:
            info['rows'] = _series(recorded, b['metric_codes'], b['granularity'], b['aggregation'], start, end)
        items.append(info)
    return {'start': start.isoformat(), 'end': end.isoformat(), 'blocks': items,
            'source_status': status_summary(db, unit_id, needed, end) if unit_id is not None else None,
            'readings_available': len(recorded), 'time_zone': 'Asia/Makassar'}
