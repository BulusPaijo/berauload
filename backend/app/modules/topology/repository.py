"""Topology persistence and constrained readings access, isolated from HTTP."""
from datetime import date
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from ...db import Asset, HourRecord, Metric, Reading
from ..org_units.models import UnitDayState
from ..engineering.models import EngineeringRule
from .models import TopologyDiagram, TopologyRevision
from ..org_units.references import unit_ids


def list_diagrams(db: Session, unit_id: int):
    return db.query(TopologyDiagram).filter_by(archived=False, unit_id=unit_id).order_by(
        TopologyDiagram.name, TopologyDiagram.id).all()


def diagram(db: Session, diagram_id: int, unit_id: int):
    return db.query(TopologyDiagram).filter_by(id=diagram_id, unit_id=unit_id).first()


def references(db: Session, unit_id: int):
    home_id=unit_id
    assets = {r.code: r.id for r in db.query(Asset).filter(Asset.unit_id==home_id, Asset.active.is_(True))}
    metrics = {r.code: (r.unit, r.asset_id) for r in db.query(Metric).filter(
        Metric.active.is_(True),Metric.unit_id.in_(unit_ids(db, home_id)))}
    rules = {r.id: r for r in db.query(EngineeringRule).filter_by(status='active', unit_id=unit_id)}
    return assets, metrics, rules


def add_revision(db: Session, item: TopologyDiagram, actor: int):
    snap = {'name': item.name, 'description': item.description, 'layout': item.layout}
    db.add(TopologyRevision(diagram_id=item.id, version=item.version,
                            snapshot=snap, updated_by=actor))


def revision_list(db: Session, diagram_id: int):
    return db.query(TopologyRevision).filter_by(diagram_id=diagram_id).order_by(
        TopologyRevision.version.desc()).all()


def revision(db: Session, diagram_id: int, version: int):
    return db.query(TopologyRevision).filter_by(diagram_id=diagram_id, version=version).first()


def compare_and_swap(db: Session, item: TopologyDiagram, expected: int, values: dict):
    result = db.execute(update(TopologyDiagram).where(
        TopologyDiagram.id == item.id, TopologyDiagram.version == expected).values(
        **values, version=expected + 1))
    return result.rowcount == 1


def day_status(db: Session, day: date, unit_id: int) -> str:
    record = db.query(UnitDayState).filter_by(unit_id=unit_id,day=day).first()
    return record.status if record else 'draft'


def read_hour(db: Session, day: date, hour: int, codes: set[str], unit_id: int):
    if not codes:
        return {}
    rows = db.execute(select(Metric.code, Reading.value).join(
        Reading, Reading.metric_id == Metric.id).join(
        HourRecord, HourRecord.id == Reading.hour_id).where(
        HourRecord.day == day, HourRecord.hour == hour,
        Metric.code.in_(codes),Metric.unit_id.in_(unit_ids(db, unit_id, active_only=False)))).all()
    return {code: float(value) for code, value in rows}


def read_day(db: Session, day: date, codes: set[str], unit_id: int):
    if not codes:
        return {}
    rows = db.execute(select(HourRecord.hour, Metric.code, Reading.value).join(
        Reading, Reading.hour_id == HourRecord.id).join(
        Metric, Metric.id == Reading.metric_id).where(
        HourRecord.day == day, Metric.code.in_(codes),Metric.unit_id.in_(unit_ids(db, unit_id, active_only=False)))).all()
    return {(hour, code): float(value) for hour, code, value in rows}
