"""Private/shared analysis views and global reference-column setting."""
from sqlalchemy import Boolean, Column, ForeignKey, Integer, JSON, String, UniqueConstraint
from ...db import Base


class GarduAnalysisSettings(Base):
    __tablename__ = 'gardu_analysis_settings'
    id = Column(Integer, primary_key=True)
    reference_column_id = Column(Integer, ForeignKey('gardu_calc_columns.id'), nullable=False)


class GarduAnalysisView(Base):
    __tablename__ = 'gardu_analysis_views'
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    name = Column(String(150), nullable=False)
    shared = Column(Boolean, nullable=False, default=False)
    is_default = Column(Boolean, nullable=False, default=False)
    layout = Column(JSON, nullable=False)
    __table_args__ = (UniqueConstraint('owner_id', 'name', name='uq_gardu_analysis_owner_name'),)
