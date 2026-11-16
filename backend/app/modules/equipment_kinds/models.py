"""Stable kind codes used by Asset.kind; names are user-configurable."""
from sqlalchemy import Boolean, Column, Integer, String
from ...db import Base


class EquipmentKind(Base):
    __tablename__ = 'equipment_kinds'
    id = Column(Integer, primary_key=True)
    code = Column(String(35), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    display_order = Column(Integer, nullable=False, default=0)
