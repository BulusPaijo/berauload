"""Stage 5: read-only descendant metric references, independent of actor privileges.

A parent configuration can refer to its own metrics or descendants, never to
ancestors or siblings. Authorization of the *owner unit* remains unit_context.
"""
from datetime import date
from fastapi import HTTPException
from ...db import Metric
from .models import OrgUnit, UnitDayState
from .service import descendants


def unit_ids(db, owner_id: int, *, children_only=False, active_only=True):
    rows = db.query(OrgUnit).all()
    owner = next((row for row in rows if row.id == owner_id), None)
    if owner is None:
        raise HTTPException(404, 'Unit tidak ditemukan')
    values = [row for row in rows if row.id in set(descendants(owner_id, [
        {'id': u.id, 'parent_id': u.parent_id, 'level': u.level} for u in rows]))]
    if not children_only:
        values.insert(0, owner)
    return [r.id for r in values if not active_only or r.active]


def metric_catalog(db, owner_id: int, include_inactive=False):
    allowed = unit_ids(db, owner_id, active_only=not include_inactive)
    query = db.query(Metric).filter(Metric.unit_id.in_(allowed))
    if not include_inactive:
        query = query.filter(Metric.active.is_(True))
    return {row.code: row for row in query.all()}


def validate_codes(db, owner_id: int, codes, include_inactive=False):
    catalog = metric_catalog(db, owner_id, include_inactive)
    invalid = set(codes) - catalog.keys()
    if invalid:
        raise HTTPException(404, 'Parameter di luar unit atau unit turunannya')
    return {code: catalog[code] for code in codes}


def sources(db, owner_id: int, codes):
    """Traverse explicit formula dependencies, never infer an automatic subtotal."""
    from ..formulas.models import FormulaDefinition
    from ..formulas.engine import parse_formula
    metrics = metric_catalog(db, owner_id, include_inactive=True)
    direct = validate_codes(db, owner_id, codes, include_inactive=True)
    parents = {m.metric_id: m for m in db.query(FormulaDefinition).all()}
    seen, source_ids = set(), set()

    def visit(code):
        if code in seen:
            return
        seen.add(code)
        metric = metrics.get(code)
        if metric is None:
            return
        if metric.unit_id != owner_id:
            source_ids.add(metric.unit_id)
        definition = parents.get(metric.id)
        if definition:
            for ref in parse_formula(definition.expression)[1]:
                visit(ref)

    for code in direct:
        visit(code)
    return sorted(source_ids)


def status_summary(db, owner_id: int, codes, day: date):
    ids = sources(db, owner_id, codes)
    units = {u.id: u for u in db.query(OrgUnit).filter(OrgUnit.id.in_(ids)).all()}
    states = {r.unit_id: r.status for r in db.query(UnitDayState).filter(
        UnitDayState.unit_id.in_(ids), UnitDayState.day == day).all()}
    items = [{'unit_id': uid, 'unit': units[uid].name,
              'status': states.get(uid, 'draft')} for uid in ids]
    counts = {value: sum(item['status'] == value for item in items)
              for value in ('final', 'verified', 'draft')}
    return {'date': day.isoformat(), 'counts': counts, 'units': items}


def unit_tree_metrics(db, owner_id: int):
    allowed = unit_ids(db, owner_id)
    units = {r.id: r for r in db.query(OrgUnit).filter(OrgUnit.id.in_(allowed)).all()}
    catalog = metric_catalog(db, owner_id)
    return [{'id': m.id, 'code': m.code, 'name': m.name, 'unit': m.unit,
             'active': m.active, 'group': m.group_name, 'mode': m.input_mode,
             'asset_id': m.asset_id, 'unit_id': m.unit_id,
             'unit_name': units[m.unit_id].name, 'unit_level': units[m.unit_id].level,
             'role_key': m.role_key, 'source': m.unit_id != owner_id,
             'label': f'{units[m.unit_id].name} - {m.name}'}
            for m in sorted(catalog.values(), key=lambda m: (allowed.index(m.unit_id), m.name))]
