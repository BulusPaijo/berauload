"""Stage 7 additive, recorded migration; never alter existing session values."""
from sqlalchemy import inspect, text, select
from ..formulas.models import SchemaMigration
from .models import LoginAttempt

VERSION = '20261116_17_stage7_session_safety'


def run(engine):
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        if conn.execute(select(SchemaMigration.version).where(
                SchemaMigration.version == VERSION)).scalar_one_or_none():
            return
        LoginAttempt.__table__.create(conn, checkfirst=True)
        existing = {column['name'] for column in inspect(conn).get_columns('login_sessions')}
        if 'last_seen_at' not in existing:
            conn.execute(text('ALTER TABLE login_sessions ADD COLUMN last_seen_at TIMESTAMP'))
        conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
