"""Stage 9d-2 additive, idempotent: template table only."""
from sqlalchemy import select
from ..formulas.models import SchemaMigration
from .export_models import GarduExportTemplate

VERSION = '20261117_21_stage9d2_export_templates'


def run(engine):
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        GarduExportTemplate.__table__.create(conn, checkfirst=True)
        if conn.execute(select(SchemaMigration.version).where(
                SchemaMigration.version == VERSION)).first():
            return
        conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
