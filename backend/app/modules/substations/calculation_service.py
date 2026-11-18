"""Gardu-only calculation over snapshots and stored readings; no writes to measured data."""
from datetime import date, datetime
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, or_, text
from ..formulas.engine import evaluate_gardu, FormulaError
from ...db import now
from .models import SubstationMeasurement, SubstationParam, SubstationValue
from .models_calc import (GarduCalcColumn, GarduCalcConstant, GarduCalcRule,
    GarduCalcSettings, GarduCalcValue, GarduCalcMatch, GarduCalcMark)
from .calculation_rules import order_columns
from .common import dump


def prepare(db):
    """One definition snapshot per batch, with explicit dependency checking."""
    return {'columns': order_columns(db),
            'rules': db.query(GarduCalcRule).filter_by(active=True).order_by(
                GarduCalcRule.display_order, GarduCalcRule.id).all(),
            'params': db.query(SubstationParam).all(),
            'constants': db.query(GarduCalcConstant).filter_by(active=True).all(),
            'cells': None}


def context(db, measurement, prepared=None):
    """Empty/flagged cells are NULL; physically absent lines are not missing."""
    conf = prepared or prepare(db)
    variables = {'kva': float(measurement.snapshot_power_kva),
                 'fase': float(measurement.snapshot_phase),
                 'jumlah_jurusan': float(measurement.snapshot_line_count)}
    aggregates, flags, absent = {}, {}, set()
    if conf['cells'] is None:
        rows = db.query(SubstationValue).filter_by(measurement_id=measurement.id).all()
    else:
        rows = conf['cells'].get(measurement.id, [])
    cells = {(r.param_id, r.line_no): r for r in rows}
    for param in conf['params']:
        code = param.code.lower()
        if param.scope == 'line':
            values = []
            for index in range(1, 6):
                key = f'{code}_j{index}'
                if index > measurement.snapshot_line_count:
                    absent.add(key)
                    continue
                row = cells.get((param.id, index))
                value = (float(row.value) if row and row.value is not None and not row.flag
                         else None)
                variables[key] = value
                values.append(value)
                flags[key] = {row.flag.lower()} if row and row.flag else set()
            aggregates[code] = values
            flags[code] = set().union(*(flags[f'{code}_j{i}'] for i in range(
                1, measurement.snapshot_line_count + 1)))
        else:
            row = cells.get((param.id, 0))
            variables[code] = float(row.value) if row and row.value is not None and not row.flag else None
            flags[code] = {row.flag.lower()} if row and row.flag else set()
    for constant in conf['constants']:
        variables[constant.code] = float(constant.value)
    return variables, aggregates, flags, absent


def compute(db, measurement, draft=None, prepared=None):
    """No writes. Draft cycles raise 422; damaged stored definitions are noted."""
    fallback = None
    if draft:
        ordered = order_columns(db, draft)  # do not silently ignore a draft cycle
    else:
        try:
            ordered = (prepared or prepare(db))['columns']
        except HTTPException as exc:
            fallback = f'Urutan rumus tersimpan rusak: {exc.detail}'
            ordered = db.query(GarduCalcColumn).filter_by(active=True).order_by(
                GarduCalcColumn.display_order).all()
    conf = prepared or prepare_for_fallback(db, ordered)
    variables, aggregates, flags, absent = context(db, measurement, conf)
    values = []
    for col in ordered:
        not_applicable = set()
        try:
            result, missing, n, total = evaluate_gardu(
                col.expression, variables, aggregates, flags,
                skip_missing=col.empty_mode == 'lewati',
                absent_lines=absent, not_applicable=not_applicable)
            incomplete = bool(missing)
            note = (f'tidak lengkap ({n} dari {total} sumber terisi)' if incomplete
                    else ('Hasil NULL: pembagian nol/operan tidak valid' if result is None else ''))
            if result is None and not_applicable:
                note = '; '.join(f'jurusan {x.rsplit("_j", 1)[-1]} tidak ada pada gardu ini'
                                 for x in sorted(not_applicable))
            if result is not None and isinstance(result, bool):
                result, note = None, 'Hasil kolom harus angka, bukan kondisi logis'
        except (FormulaError, ValueError, TypeError, ArithmeticError) as exc:
            result, missing, n, total, incomplete = None, [], 0, 0, False
            note = 'Rumus gagal: ' + str(exc)[:180]
        if fallback: note = f'{fallback}; {note}'.strip('; ')
        values.append({'column_id': getattr(col, 'id', None), 'code': col.code,
            'value': result, 'incomplete': incomplete, 'filled': n, 'total': total,
            'missing': missing, 'note': note, 'unit': col.unit, 'decimals': col.decimals})
        variables[col.code] = result
    matches, category = [], {}
    for rule in conf['rules']:
        expression = (draft['expression'] if draft and draft.get('kind') == 'rule'
                      and rule.code == draft['code'] else rule.expression)
        try:
            result, _, _, _ = evaluate_gardu(expression, variables, aggregates, flags,
                                              absent_lines=absent)
        except (FormulaError, ValueError, TypeError, ArithmeticError): result = None
        if not isinstance(result, bool) or not result: continue
        if rule.kind == 'category':
            if rule.group_name in category: continue
            category[rule.group_name] = rule.code
        matches.append({'id':rule.id,'code':rule.code,'name':rule.name,
                        'kind':rule.kind,'group_name':rule.group_name,
                        'color':rule.color,'marker':rule.marker})
    for group in {r.group_name for r in conf['rules'] if r.kind == 'category'}:
        category.setdefault(group, 'tidak_dapat_dinilai')
    return {'columns':values,'matches':matches,'categories':category}


def prepare_for_fallback(db, ordered):
    """Read current definitions even if a legacy stored dependency cycle exists."""
    return {'columns':ordered,'rules':db.query(GarduCalcRule).filter_by(active=True).order_by(
        GarduCalcRule.display_order, GarduCalcRule.id).all(),
        'params':db.query(SubstationParam).all(),
        'constants':db.query(GarduCalcConstant).filter_by(active=True).all(),'cells':None}


def save_results(db, measurement, version=None, prepared=None):
    """Serializes results on the parent measurement row (Postgres).

    Derived results only. A concurrent newer definition version is never downgraded.
    """
    if db.bind.dialect.name == 'postgresql':
        db.query(SubstationMeasurement.id).filter_by(id=measurement.id).with_for_update().first()
    settings = db.get(GarduCalcSettings, 1)
    if settings is None: return None
    version = version or settings.version
    mark = db.get(GarduCalcMark, measurement.id)
    if mark and mark.version > version: return None
    result = compute(db, measurement, prepared=prepared)
    # Locked parent prevents conflicting writers in PostgreSQL. Savepoint makes
    # an unexpected unique-index race recoverable without poisoning the session.
    for attempt in range(2):
        try:
            with db.begin_nested():
                db.query(GarduCalcValue).filter_by(measurement_id=measurement.id).delete(
                    synchronize_session=False)
                db.query(GarduCalcMatch).filter_by(measurement_id=measurement.id).delete(
                    synchronize_session=False)
                for item in result['columns']:
                    if item['column_id'] is None: continue
                    db.add(GarduCalcValue(measurement_id=measurement.id,
                        column_id=item['column_id'], value=item['value'],
                        incomplete=item['incomplete'], filled=item['filled'],
                        total=item['total'], note=item['note'], version=version))
                for item in result['matches']:
                    db.add(GarduCalcMatch(measurement_id=measurement.id,
                        rule_id=item['id'], version=version))
                if not mark:
                    mark = GarduCalcMark(measurement_id=measurement.id,
                                         version=version, calculated_at=now())
                    db.add(mark)
                else:
                    mark.version, mark.calculated_at = version, now()
                db.flush()
            break
        except IntegrityError as exc:
            db.expire_all()
            mark = db.get(GarduCalcMark, measurement.id)
            if mark and mark.version > version: return None
            if attempt == 1:
                raise HTTPException(409, 'Hasil hitung sedang diperbarui, ulangi') from exc
    return result


def get_results(db, measurement_id):
    settings = db.get(GarduCalcSettings, 1)
    mark = db.get(GarduCalcMark, measurement_id)
    version = settings.version if settings else 0
    values = db.query(GarduCalcValue, GarduCalcColumn).join(
        GarduCalcColumn, GarduCalcValue.column_id == GarduCalcColumn.id).filter(
        GarduCalcValue.measurement_id == measurement_id,
        GarduCalcColumn.active.is_(True)).order_by(GarduCalcColumn.display_order).all()
    matches = db.query(GarduCalcMatch, GarduCalcRule).join(
        GarduCalcRule, GarduCalcMatch.rule_id == GarduCalcRule.id).filter(
        GarduCalcMatch.measurement_id == measurement_id).order_by(GarduCalcRule.display_order).all()
    return {'version': mark.version if mark else None, 'latest_version': version,
        'stale': not mark or mark.version < version,
        'columns': [{'code': c.code, 'name': c.name, 'unit': c.unit, 'decimals': c.decimals,
                     'value': v.value, 'incomplete': v.incomplete, 'filled': v.filled,
                     'total': v.total, 'note': v.note} for v,c in values],
        'matches': [{'code': r.code, 'name': r.name, 'kind': r.kind,
                     'group_name': r.group_name, 'color': r.color, 'marker': r.marker}
                    for _,r in matches if r.active]}


def pending_query(db, version):
    return db.query(SubstationMeasurement).outerjoin(
        GarduCalcMark, SubstationMeasurement.id == GarduCalcMark.measurement_id
        ).filter(or_(GarduCalcMark.measurement_id.is_(None),
                     GarduCalcMark.version < version))


def recalc_status(db):
    settings = db.get(GarduCalcSettings, 1)
    if not settings: return {'version': 0, 'total': 0, 'completed': 0, 'remaining': 0}
    total = db.query(func.count(SubstationMeasurement.id)).scalar() or 0
    completed = db.query(func.count(GarduCalcMark.measurement_id)).filter(GarduCalcMark.version >= settings.version).scalar() or 0
    return {'version': settings.version, 'total': total, 'completed': completed,
            'remaining': max(0, total - completed), 'stale_days': settings.stale_days}


def recalc_batch(db, limit=100):
    settings = db.get(GarduCalcSettings, 1)
    if settings is None: return {'busy':False,'processed':0,**recalc_status(db)}
    if db.bind.dialect.name == 'postgresql':
        locked = db.execute(text('SELECT pg_try_advisory_xact_lock(:key)'),
                            {'key': 912001609}).scalar()
        if not locked:
            # Progress is still readable even when another worker owns the lock.
            return {'busy':True,'processed':0,**recalc_status(db)}
    query = pending_query(db, settings.version).order_by(SubstationMeasurement.id)
    if db.bind.dialect.name == 'postgresql':
        # Lock only measurement rows, not outer-joined marks.
        query = query.with_for_update(of=SubstationMeasurement, skip_locked=True)
    pending = query.limit(limit).all()
    config = prepare(db)
    ids = [m.id for m in pending]
    grouped = {mid: [] for mid in ids}
    if ids:
        for value in db.query(SubstationValue).filter(SubstationValue.measurement_id.in_(ids)):
            grouped[value.measurement_id].append(value)
    config['cells'] = grouped
    for measurement in pending:
        save_results(db, measurement, settings.version, config)
    status = recalc_status(db)
    settings.pending = status['remaining'] > 0
    return {'busy':False,'processed':len(pending),**status}


def latest_visits(db, cap=150, scan_cap=3000):
    seen, result = set(), []
    rows = db.query(SubstationMeasurement).order_by(
        SubstationMeasurement.measured_on.desc(),
        SubstationMeasurement.id.desc()).limit(scan_cap).all()
    for row in rows:
        if row.substation_id in seen: continue
        seen.add(row.substation_id)
        result.append(row)
        if len(result) >= cap: break
    more = len(rows) == scan_cap or len(result) >= cap
    return result, more


def stale_days(db, station_id, current_day=None):
    settings = db.get(GarduCalcSettings, 1)
    last = db.query(func.max(SubstationMeasurement.measured_on)).filter_by(
        substation_id=station_id).scalar()
    if not settings: return False
    return not last or ((current_day or datetime.now(ZoneInfo('Asia/Makassar')).date()) - last).days > settings.stale_days
