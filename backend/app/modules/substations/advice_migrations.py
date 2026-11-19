"""Stage 9e additive, idempotent: `plan` column on follow-ups and two task types.

Types are inserted only when missing, so admin edits (name, suggestion, active) survive restarts.
"""
from sqlalchemy import inspect, select, text
from ..formulas.models import SchemaMigration
from .followup_models import GarduFollowup, GarduFollowupType

VERSION = '20261119_30_stage9e_advice'
TYPES = [('tukar_trafo', 'Tukar trafo', ['overload']), ('pindah_beban', 'Pindah beban', ['overload'])]


def run(engine):
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        GarduFollowupType.__table__.create(conn, checkfirst=True)
        GarduFollowup.__table__.create(conn, checkfirst=True)
        columns = {c['name'] for c in inspect(conn).get_columns(GarduFollowup.__tablename__)}
        if 'plan' not in columns:
            kind = 'JSONB' if conn.dialect.name == 'postgresql' else 'JSON'
            conn.execute(text(f'ALTER TABLE {GarduFollowup.__tablename__} ADD COLUMN plan {kind}'))
        if conn.execute(select(SchemaMigration.version).where(SchemaMigration.version == VERSION)).first():
            return
        existing = {r[0] for r in conn.execute(select(GarduFollowupType.code))}
        order = conn.execute(select(GarduFollowupType.id)).fetchall()
        for offset, (code, name, suggest) in enumerate(TYPES):
            if code not in existing:
                conn.execute(GarduFollowupType.__table__.insert().values(
                    code=code, name=name, suggest_for=suggest,
                    display_order=len(order) + offset, active=True))
        conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
