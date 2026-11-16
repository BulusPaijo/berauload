"""Equipment category persistence."""
from sqlalchemy.orm import Session
from .models import EquipmentKind


def all_kinds(db: Session):
    return db.query(EquipmentKind).order_by(
        EquipmentKind.display_order, EquipmentKind.name).all()


def by_code(db: Session, code: str):
    return db.query(EquipmentKind).filter_by(code=code).first()
