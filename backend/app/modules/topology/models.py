"""Configuration-only topology tables. They never own readings or switching states."""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from ...db import Base, now


class TopologyDiagram(Base):
    __tablename__ = 'topology_diagrams'
    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=True)
    name = Column(String(150), nullable=False)
    description = Column(String(500), nullable=False, default='')
    layout = Column(JSON, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    archived = Column(Boolean, nullable=False, default=False)
    updated_by = Column(ForeignKey('users.id'), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=now, onupdate=now)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)


class TopologyRevision(Base):
    __tablename__ = 'topology_revisions'
    id = Column(Integer, primary_key=True)
    diagram_id = Column(ForeignKey('topology_diagrams.id'), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    snapshot = Column(JSON, nullable=False)
    updated_by = Column(ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)
    __table_args__ = (UniqueConstraint('diagram_id', 'version', name='uq_topology_revision'),)
