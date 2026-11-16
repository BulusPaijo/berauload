"""Additive migration; explicitly no topology seed and no change to measurement tables."""
from sqlalchemy import select
from ..formulas.models import SchemaMigration
from .models import TopologyDiagram, TopologyRevision

VERSION = '20261114_10_topology_stage1'


def run(engine):
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        TopologyDiagram.__table__.create(conn, checkfirst=True)
        TopologyRevision.__table__.create(conn, checkfirst=True)
        exists = conn.execute(select(SchemaMigration.version).where(
            SchemaMigration.version == VERSION)).scalar_one_or_none()
        if exists is None:
            conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
