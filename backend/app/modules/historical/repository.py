"""SQL operations for saved historical definitions; readings remain read-only."""
from sqlalchemy.orm import Session
from ...db import HourRecord, Metric, Reading
from .models import HistoricalDefinition, HistoricalRevision
from ..org_units.references import unit_ids


def catalog_units(db: Session, include_inactive: bool = False,unit_id=None) -> dict[str, str]:
    query = db.query(Metric)
    if unit_id is not None:
        query = query.filter(Metric.unit_id.in_(unit_ids(db, unit_id, active_only=not include_inactive)))
    if not include_inactive:
        query = query.filter(Metric.active.is_(True))
    return {item.code: item.unit for item in query}


def get_definitions(db: Session, include_archived: bool = False, unit_id=None):
    query = db.query(HistoricalDefinition).filter_by(unit_id=unit_id)
    if not include_archived:
        query = query.filter(HistoricalDefinition.archived.is_(False))
    return query.order_by(HistoricalDefinition.id.desc()).all()


def get_definition(db: Session, definition_id: int, unit_id=None):
    return db.query(HistoricalDefinition).filter_by(id=definition_id, unit_id=unit_id).first()


def get_revision(db: Session, definition_id: int, version: int):
    return db.query(HistoricalRevision).filter_by(definition_id=definition_id, version=version).first()


def list_revisions(db: Session, definition_id: int):
    return db.query(HistoricalRevision).filter_by(definition_id=definition_id).order_by(HistoricalRevision.version.desc()).all()


def code_exists(db: Session, code: str) -> bool:
    return db.query(HistoricalDefinition.id).filter_by(code=code).first() is not None


def add_definition(db: Session, fields: dict, user_id: int):
    item = HistoricalDefinition(**fields, created_by=user_id)
    db.add(item)
    db.flush()
    snapshot = {key: fields[key] for key in ('code', 'name', 'expression', 'unit',
                'aggregation', 'resolution', 'mode', 'moving_days', 'hour_start', 'hour_end')}
    db.add(HistoricalRevision(definition_id=item.id, version=1, snapshot=snapshot,
                              reason='Versi awal', created_by=user_id))
    return item


def iter_readings(db: Session, codes: frozenset[str], start, end, unit_id=None):
    query = (db.query(HourRecord.day, HourRecord.hour, Metric.code, Reading.value)
             .join(Reading, Reading.hour_id == HourRecord.id)
             .join(Metric, Reading.metric_id == Metric.id)
             .filter(HourRecord.day >= start, HourRecord.day <= end, Metric.code.in_(codes))
             .order_by(HourRecord.day, HourRecord.hour, Metric.code))
    if unit_id is not None:
        query=query.filter(Metric.unit_id.in_(unit_ids(db, unit_id, active_only=False)))
    return query.yield_per(2000)
