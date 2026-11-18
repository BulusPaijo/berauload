"""SQL-only selection/filter/sort. No Python per-station N+1 or JSON sorting."""
from datetime import date, timedelta
from fastapi import HTTPException
from sqlalchemy import and_, case, exists, func, literal, or_, select
from sqlalchemy.orm import aliased
from .common import child_ids, dump
from .models import Substation, SubstationFeeder, SubstationMeasurement
from .models_calc import (GarduCalcColumn, GarduCalcMatch, GarduCalcMark,
                          GarduCalcRule, GarduCalcSettings, GarduCalcValue)
from .analysis_models import GarduAnalysisSettings


def reference(db):
    settings = db.get(GarduAnalysisSettings, 1)
    return db.get(GarduCalcColumn, settings.reference_column_id) if settings else None


def _selected(db, opt, allowed):
    m = SubstationMeasurement
    base = db.query(m.id.label('mid'), m.substation_id.label('sid'),
                    m.session.label('sesi'), m.measured_on.label('day'))\
        .filter(m.unit_id.in_(allowed))
    if opt.mode == 'periode':
        if not opt.start or not opt.end:
            raise HTTPException(422, 'Mode periode membutuhkan tanggal mulai dan akhir')
        base = base.filter(m.measured_on.between(opt.start, opt.end))
    if opt.mode == 'semua':
        if opt.start: base = base.filter(m.measured_on >= opt.start)
        if opt.end: base = base.filter(m.measured_on <= opt.end)
        if opt.session != 'tertinggi': base = base.filter(m.session == opt.session)
        return base.subquery()
    latest = base
    # Window ranks are computed after applying period, before selecting session.
    dated = latest.add_columns(func.row_number().over(
        partition_by=(m.substation_id, m.session),
        order_by=(m.measured_on.desc(), m.id.desc())).label('rn')).subquery()
    choose = db.query(dated.c.mid, dated.c.sid, dated.c.sesi, dated.c.day).filter(
        dated.c.rn == 1)
    if opt.session != 'tertinggi': choose = choose.filter(dated.c.sesi == opt.session)
    candidates = choose.subquery()
    ref = reference(db)
    v = aliased(GarduCalcValue)
    if ref:
        weight = v.value
        ranked = db.query(candidates.c.mid, candidates.c.sid,
            func.row_number().over(partition_by=candidates.c.sid,
                order_by=(case((weight.is_(None), 1), else_=0), weight.desc(),
                          candidates.c.day.desc(), candidates.c.mid.desc())).label('rank'))\
            .outerjoin(v, and_(v.measurement_id == candidates.c.mid,
                                v.column_id == ref.id)).subquery()
    else:
        ranked = db.query(candidates.c.mid, candidates.c.sid,
            func.row_number().over(partition_by=candidates.c.sid,
                order_by=(candidates.c.day.desc(), candidates.c.mid.desc())).label('rank')).subquery()
    return db.query(ranked.c.mid, ranked.c.sid).filter(ranked.c.rank == 1).subquery()


def _rule_filter(db, measurement_id, code):
    return exists().where(and_(GarduCalcMatch.measurement_id == measurement_id,
        GarduCalcMatch.rule_id == GarduCalcRule.id,
        GarduCalcRule.code == code, GarduCalcRule.active.is_(True)))


def _apply_filters(db, query, opt, measurement_id, last_date):
    m, s = SubstationMeasurement, Substation
    if opt.feeder_id: query = query.filter(s.feeder_id == opt.feeder_id)
    if opt.min_kva is not None: query = query.filter(s.power_kva >= opt.min_kva)
    if opt.max_kva is not None: query = query.filter(s.power_kva <= opt.max_kva)
    if opt.text:
        word = f'%{opt.text.strip()}%'
        query = query.filter(or_(s.code.ilike(word), s.name.ilike(word),
                                 s.address.ilike(word), s.brand.ilike(word)))
    if opt.state: query = query.filter(m.state == opt.state)
    days = (db.get(GarduCalcSettings, 1).stale_days if db.get(GarduCalcSettings, 1) else 180)
    from datetime import datetime
    from zoneinfo import ZoneInfo
    cutoff = datetime.now(ZoneInfo('Asia/Makassar')).date() - timedelta(days=days)
    if opt.status == 'belum': query = query.filter(last_date.is_(None))
    if opt.status == 'lama': query = query.filter(last_date < cutoff)
    if opt.status == 'baru': query = query.filter(last_date >= cutoff)
    if opt.category:
        if opt.category == 'tidak_dapat_dinilai':
            active_categories = select(GarduCalcRule.id).where(
                GarduCalcRule.kind == 'category', GarduCalcRule.active.is_(True))
            found = exists().where(and_(GarduCalcMatch.measurement_id == measurement_id,
                     GarduCalcMatch.rule_id.in_(active_categories)))
            query = query.filter(~found)
        else:
            query = query.filter(_rule_filter(db, measurement_id, opt.category))
    if opt.findings:
        tests = [_rule_filter(db, measurement_id, code) for code in opt.findings]
        query = query.filter(and_(*tests) if opt.finding_mode == 'all' else or_(*tests))
    if opt.numeric_code:
        col = db.query(GarduCalcColumn).filter_by(code=opt.numeric_code, active=True).first()
        if not col: raise HTTPException(422, 'Kolom hitung tidak dikenal/diarsipkan')
        v = aliased(GarduCalcValue)
        # EXISTS correlates to the SELECTED measurement id (chosen.c.mid), not
        # to the original measurements table. A scalar subquery here returns
        # multiple values on PostgreSQL and an arbitrary first value on SQLite.
        present = select(literal(1)).select_from(v).where(
            v.measurement_id == measurement_id, v.column_id == col.id)
        if opt.numeric_op == 'kosong':
            query = query.filter(~present.where(v.value.isnot(None)).exists())
        elif opt.numeric_op == 'ada':
            query = query.filter(present.where(v.value.isnot(None)).exists())
        else:
            if opt.numeric_op == 'gte': condition = v.value >= opt.numeric_min
            elif opt.numeric_op == 'lte': condition = v.value <= opt.numeric_min
            else: condition = v.value.between(opt.numeric_min, opt.numeric_max)
            query = query.filter(present.where(condition).exists())
    return query


def filtered(db, ctx, opt):
    if opt.mode not in ('terakhir','periode','semua'):
        raise HTTPException(422, 'Mode analisa tidak dikenal')
    allowed = child_ids(db, ctx)
    if opt.unit_id:
        if opt.unit_id not in allowed: raise HTTPException(404, 'Unit tidak ditemukan')
        # Parent unit selection inherits descendants.
        from ..org_units.models import OrgUnit
        current = db.get(OrgUnit, opt.unit_id)
        queue, descendants = [current.id], [current.id]
        while queue:
            next_ids = [r.id for r in db.query(OrgUnit).filter(
                OrgUnit.parent_id.in_(queue), OrgUnit.active.is_(True)).all()]
            descendants.extend(next_ids)
            queue = next_ids
        allowed = [u for u in descendants if u in allowed]
    chosen = _selected(db, opt, allowed)
    last = db.query(SubstationMeasurement.substation_id.label('sid'),
        func.max(SubstationMeasurement.measured_on).label('day')).filter(
        SubstationMeasurement.unit_id.in_(allowed)).group_by(
        SubstationMeasurement.substation_id).subquery()
    query = db.query(Substation.id.label('sid'), chosen.c.mid.label('mid'),
        last.c.day.label('last_day'), Substation.feeder_id.label('feeder_id'))\
        .select_from(Substation).outerjoin(chosen, chosen.c.sid == Substation.id)\
        .outerjoin(last, last.c.sid == Substation.id)\
        .outerjoin(SubstationMeasurement, SubstationMeasurement.id == chosen.c.mid)\
        .filter(Substation.active.is_(True), Substation.unit_id.in_(allowed))
    if opt.mode == 'semua': query = query.filter(chosen.c.mid.isnot(None))
    return _apply_filters(db, query, opt, chosen.c.mid, last.c.day)


def sorted_query(db, query, opt):
    s, m = Substation, SubstationMeasurement
    mapping = {'code':s.code, 'name':s.name,'feeder':s.feeder_id,
               'power_kva':s.power_kva, 'measured_on':m.measured_on,
               'session':m.session,'state':m.state, 'brand':s.brand, 'address':s.address}
    value = mapping.get(opt.sort)
    if value is None and opt.sort.startswith('extra_'):
        from .models import SubstationField
        field = db.query(SubstationField).filter_by(code=opt.sort[6:],active=True).first()
        if not field:raise HTTPException(422,'Atribut gardu tidak dikenal')
        value = (s.extra_values[opt.sort[6:]].as_float() if field.kind=='number'
                 else s.extra_values[opt.sort[6:]].as_string())
    if value is None:
        col = db.query(GarduCalcColumn).filter_by(code=opt.sort, active=True).first()
        if not col: raise HTTPException(422, 'Kolom sortir tidak dikenal')
        v = aliased(GarduCalcValue)
        query = query.outerjoin(v, and_(v.measurement_id == m.id,
                                        v.column_id == col.id))
        value = v.value
    ordering = value.desc() if opt.desc else value.asc()
    return query.order_by(case((value.is_(None),1),else_=0), ordering,
                          s.code.asc(), m.id.desc())


def rows(db, query, opt, page_size=None):
    total = query.order_by(None).count()
    ordered = sorted_query(db, query, opt)
    if page_size:
        ordered = ordered.offset((opt.page-1)*page_size).limit(page_size)
    return total, ordered.all()
