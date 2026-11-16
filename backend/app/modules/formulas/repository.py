"""All persistence operations for formulas live here."""
from sqlalchemy.orm import Session
from ...db import Asset, Metric
from .models import FormulaDefinition


def list_formulas(db: Session):
    return (db.query(FormulaDefinition, Metric)
            .join(Metric, Metric.id == FormulaDefinition.metric_id)
            .order_by(FormulaDefinition.id).all())


def list_metrics(db: Session):
    return db.query(Metric).order_by(Metric.display_order).all()


def next_display_order(db: Session) -> int:
    from sqlalchemy import func
    return int(db.query(func.max(Metric.display_order)).scalar() or 0) + 1


def create(db: Session, metric: Metric, expression: str, user_id: int):
    db.add(metric)
    db.flush()
    definition = FormulaDefinition(metric_id=metric.id, expression=expression, created_by=user_id)
    db.add(definition)
    return definition


def existing_asset(db: Session, asset_id: int | None) -> bool:
    return asset_id is None or db.get(Asset, asset_id) is not None
