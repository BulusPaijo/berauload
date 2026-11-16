"""Persist source changes detected while a parent day's results are locked."""
from sqlalchemy import Column, Integer, ForeignKey, Date, DateTime, UniqueConstraint
from ...db import Base, now

class UnitSourceChange(Base):
    __tablename__ = 'unit_source_changes'
    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=False)
    source_unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=False)
    day = Column(Date, nullable=False)
    hour = Column(Integer, nullable=False)
    changed_at = Column(DateTime(timezone=True), default=now, nullable=False)
    __table_args__ = (UniqueConstraint('unit_id', 'source_unit_id', 'day', 'hour',
                                      name='uq_source_change_unit_hour'),)
