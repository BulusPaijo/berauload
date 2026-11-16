"""Additive schema only; no historical rows are moved or recalculated on boot."""
from sqlalchemy import select
from ..formulas.models import SchemaMigration
from .models import UnitSourceChange

VERSION = '20261116_16_stage5_source_changes'

def run(engine):
    with engine.begin() as conn:
        UnitSourceChange.__table__.create(conn, checkfirst=True)
        SchemaMigration.__table__.create(conn, checkfirst=True)
        if not conn.execute(select(SchemaMigration.version).where(
                SchemaMigration.version == VERSION)).first():
            conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
