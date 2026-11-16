"""Idempotent, additive V1.3.0 schema migration."""
from sqlalchemy import select
from ..formulas.models import SchemaMigration
from .models import EngineeringRule, EngineeringRuleRevision

VERSION = '20261114_05_engineering_rules_core'


def run(engine):
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        EngineeringRule.__table__.create(conn, checkfirst=True)
        EngineeringRuleRevision.__table__.create(conn, checkfirst=True)
        known = conn.execute(select(SchemaMigration.version).where(SchemaMigration.version == VERSION)).first()
        if known is None:
            conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
