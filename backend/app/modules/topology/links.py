"""Resolve navigation-only links; never imply connectivity or data writes."""
from fastapi import HTTPException
from sqlalchemy.orm import Session
from ..org_units.models import OrgUnit
from ..completeness.service import allowed_units
from .models import TopologyDiagram


def validate_links(db: Session, layout: dict, owner_id: int, source_id=None):
    owner = db.get(OrgUnit, owner_id)
    if not owner:
        raise HTTPException(422, 'Unit pemilik diagram tidak ditemukan')
    symbols = [(symbol['id'], symbol['link']) for symbol in layout['symbols']
               if 'link' in symbol]
    if len(symbols) > 200:
        raise HTTPException(422, 'Maksimal 200 tautan per diagram')
    for symbol_id, link in symbols:
        unit = db.get(OrgUnit, link['unit_id'])
        target = db.get(TopologyDiagram, link['diagram_id'])
        if not unit or not unit.active or not _below(db, unit, owner.id):
            raise HTTPException(422, f'Simbol {symbol_id}: unit tujuan harus unit bawah aktif')
        if not target or target.archived or target.unit_id != unit.id:
            raise HTTPException(422, f'Simbol {symbol_id}: diagram tujuan tidak ada, berbeda unit, atau diarsipkan')
        if target.id == source_id or _reaches(db, target.id, source_id, set()):
            raise HTTPException(422, f'Simbol {symbol_id}: tautan membentuk siklus')


def _below(db: Session, unit: OrgUnit, source_id: int):
    seen = set()
    cursor = unit
    while cursor and cursor.parent_id and cursor.id not in seen:
        seen.add(cursor.id)
        if cursor.parent_id == source_id:
            return True
        cursor = db.get(OrgUnit, cursor.parent_id)
    return False


def _reaches(db: Session, diagram_id: int, wanted_id, seen: set):
    if wanted_id is None or diagram_id in seen:
        return False
    if diagram_id == wanted_id:
        return True
    seen.add(diagram_id)
    record = db.get(TopologyDiagram, diagram_id)
    if not record or record.archived:
        return False
    return any(_reaches(db, item['link']['diagram_id'], wanted_id, seen)
               for item in record.layout.get('symbols', []) if 'link' in item)


def browse(db: Session, actor, unit_id: int, include_self=True):
    items = allowed_units(db, actor, unit_id)
    if items is None:
        raise HTTPException(404, 'Unit tidak ditemukan')
    selected = [unit for unit, _ in items if include_self or unit.id != unit_id]
    ids = [unit.id for unit in selected]
    diagrams = db.query(TopologyDiagram).filter(
        TopologyDiagram.unit_id.in_(ids), TopologyDiagram.archived.is_(False)).order_by(
        TopologyDiagram.name, TopologyDiagram.id).all() if ids else []
    by_unit = {}
    for item in diagrams:
        by_unit.setdefault(item.unit_id, []).append({'id': item.id, 'name': item.name})
    return [{'unit_id': unit.id, 'unit_code': unit.code, 'unit_name': unit.name,
             'level': unit.level, 'diagrams': by_unit.get(unit.id, [])}
            for unit in selected]
