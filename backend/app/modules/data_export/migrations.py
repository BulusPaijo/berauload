"""Idempotent additive migration for V1.4.4 export templates."""
from sqlalchemy import select
from ..formulas.models import SchemaMigration
from .models import ExportTemplate

VERSION = '20261114_04_export_templates'


def run(engine):
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        ExportTemplate.__table__.create(conn, checkfirst=True)
        if conn.execute(select(SchemaMigration.version).where(
                SchemaMigration.version == VERSION)).scalar_one_or_none() is None:
            conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
