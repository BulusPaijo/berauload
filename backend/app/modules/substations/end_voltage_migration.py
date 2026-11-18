"""Stage 9d-4: tegangan ujung is measured once per gardu, not per jurusan.

Additive and idempotent. V_END_RN/SN/TN move from scope 'line' to 'substation':
- every original per-jurusan reading is copied to substation_values_archive first (nothing lost);
- per measurement the LOWEST reading is kept on line 0, so v_ujung_min / jatuh tegangan stay
  numerically identical; when only flags exist (e.g. PUTUS) the first flag is kept;
- the seeded v_ujung_min formula is updated only if the admin has not changed it.
"""
from collections import defaultdict
from sqlalchemy import Column, DateTime, Float, Integer, MetaData, String, Table, delete, func, select, update
from ..formulas.models import SchemaMigration
from .models import SubstationParam, SubstationValue
from .models_calc import GarduCalcColumn, GarduCalcHistory, GarduCalcSettings

VERSION = '20261118_23_stage9d4_end_voltage_per_gardu'
CODES = ('V_END_RN', 'V_END_SN', 'V_END_TN')
OLD = 'MIN(MIN_JURUSAN(v_end_rn), MIN_JURUSAN(v_end_sn), MIN_JURUSAN(v_end_tn))'
NEW = 'MIN(v_end_rn, v_end_sn, v_end_tn)'
NOTE = 'Tegangan ujung diukur sekali per gardu (9d-4); nilai per jurusan diarsipkan, yang terendah dipakai'
archive = Table('substation_values_archive', MetaData(),
                Column('id', Integer, primary_key=True), Column('measurement_id', Integer, nullable=False),
                Column('param_id', Integer, nullable=False), Column('line_no', Integer, nullable=False),
                Column('value', Float), Column('flag', String(40)), Column('reason', String(120), nullable=False),
                Column('archived_at', DateTime(timezone=True), server_default=func.now()))


def _merge(conn, ids):
    v = SubstationValue.__table__
    rows = conn.execute(select(v.c.measurement_id, v.c.param_id, v.c.line_no, v.c.value, v.c.flag).where(
        v.c.param_id.in_(ids)).order_by(v.c.measurement_id, v.c.param_id, v.c.line_no)).all()
    if not rows:
        return 0
    for i in range(0, len(rows), 2000):
        conn.execute(archive.insert(), [{'measurement_id': r.measurement_id, 'param_id': r.param_id,
                     'line_no': r.line_no, 'value': None if r.value is None else float(r.value), 'flag': r.flag,
                     'reason': 'stage9d4 tegangan ujung per gardu'} for r in rows[i:i + 2000]])
    keep = defaultdict(list)
    for r in rows:
        keep[(r.measurement_id, r.param_id)].append(r)
    merged = []
    for (mid, pid), group in keep.items():
        nums = [g.value for g in group if g.value is not None]
        flags = [g.flag for g in group if g.flag]
        if nums:
            merged.append({'measurement_id': mid, 'param_id': pid, 'line_no': 0, 'value': min(nums), 'flag': None})
        elif flags:
            merged.append({'measurement_id': mid, 'param_id': pid, 'line_no': 0, 'value': None, 'flag': flags[0]})
    conn.execute(delete(v).where(v.c.param_id.in_(ids)))
    for i in range(0, len(merged), 2000):
        conn.execute(v.insert(), merged[i:i + 2000])
    return len(rows)


def _convert(conn):
    params = conn.execute(select(SubstationParam.id, SubstationParam.scope).where(
        SubstationParam.code.in_(CODES))).all()
    ids = [p.id for p in params if p.scope == 'line']
    if not ids:
        return 'nothing'
    archived = _merge(conn, ids)
    conn.execute(update(SubstationParam).where(SubstationParam.id.in_(ids)).values(scope='substation'))
    col = conn.execute(select(GarduCalcColumn).where(GarduCalcColumn.code == 'v_ujung_min')).first()
    if col is not None:
        values = {}
        if col.default_expression == OLD:
            snap = dict(col.default_snapshot or {})
            if snap.get('expression') == OLD:
                snap['expression'] = NEW
            values.update(default_expression=NEW, default_snapshot=snap)
        if col.expression == OLD:
            values['expression'] = NEW
        if values:
            conn.execute(update(GarduCalcColumn).where(GarduCalcColumn.id == col.id).values(**values))
        settings = conn.execute(select(GarduCalcSettings)).first()
        conn.execute(GarduCalcHistory.__table__.insert().values(
            kind='column', code='v_ujung_min', version=settings.version if settings else 0, changed_by=None,
            before={'expression': col.expression}, after={'expression': values.get('expression', col.expression),
                                                          'note': NOTE, 'archived_values': archived}))
    return f'converted ({archived} nilai diarsipkan)'


def run(engine):
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        archive.create(conn, checkfirst=True)
        if conn.execute(select(SchemaMigration.version).where(SchemaMigration.version == VERSION)).first():
            return None
        result = _convert(conn)
        conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
        return result
