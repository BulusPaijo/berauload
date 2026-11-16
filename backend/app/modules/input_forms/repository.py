"""Database access for input presentation only."""
from ...db import Metric
from .models import InputFormTab, InputFormPlacement, InputFormRevision


def tabs(db, unit_id=None):
    return db.query(InputFormTab).filter_by(unit_id=unit_id).order_by(InputFormTab.display_order, InputFormTab.code).all()


def metrics(db, unit_id=None):
    return db.query(Metric).filter_by(unit_id=unit_id).order_by(Metric.display_order, Metric.code).all()


def placements(db, unit_id=None):
    return {p.metric_code: p for p in db.query(InputFormPlacement).filter_by(unit_id=unit_id).all()}


def revision(db, unit_id=None):
    return db.query(InputFormRevision).filter_by(unit_id=unit_id).first()
