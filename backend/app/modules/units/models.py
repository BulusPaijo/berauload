"""Versioned-safe unit registry: identifiers and conversion factors are immutable."""
from sqlalchemy import Boolean, Column, Integer, Numeric, String
from ...db import Base


class UnitDefinition(Base):
    __tablename__ = 'unit_definitions'
    id = Column(Integer, primary_key=True)
    code = Column(String(12), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    dimension = Column(String(40), nullable=False)
    factor = Column(Numeric(24, 12), nullable=False)  # multiplier to dimension base
    active = Column(Boolean, nullable=False, default=True)
    builtin = Column(Boolean, nullable=False, default=False)
