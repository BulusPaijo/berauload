"""Additive migration for the custom report template store."""
from sqlalchemy import select
from ..formulas.models import SchemaMigration
from .models import ReportTemplate

VERSION = '20261114_06_report_templates'


def run(engine):
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        ReportTemplate.__table__.create(conn, checkfirst=True)
        if not conn.execute(select(SchemaMigration.version).where(
                SchemaMigration.version == VERSION)).first():
            conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
