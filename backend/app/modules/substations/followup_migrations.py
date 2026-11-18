"""Stage 9d-3 additive, idempotent. Types seeded once; admin edits survive restarts."""
from sqlalchemy import select
from ..formulas.models import SchemaMigration
from .followup_models import GarduFollowup, GarduFollowupType

VERSION = '20261117_22_stage9d3_followups'
SEED = [
    ('penyeimbangan', 'Penyeimbangan beban', ['tidak_seimbang', 'overload_1_fasa']),
    ('uprating', 'Uprating trafo', ['overload']),
    ('mutasi', 'Mutasi trafo', ['kandidat_mutasi', 'overload']),
    ('pecah_beban', 'Pecah beban / sisip gardu', ['overload']),
    ('grounding', 'Perbaikan grounding', ['grounding']),
    ('perbaikan_jtr', 'Perbaikan JTR', ['tegangan_drop', 'jatuh_tegangan_tinggi', 'netral_tinggi']),
    ('pantau', 'Pantau', []),
]


def run(engine):
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        GarduFollowupType.__table__.create(conn, checkfirst=True)
        GarduFollowup.__table__.create(conn, checkfirst=True)
        if conn.execute(select(SchemaMigration.version).where(SchemaMigration.version == VERSION)).first():
            return
        existing = {r[0] for r in conn.execute(select(GarduFollowupType.code))}
        for order, (code, name, suggest) in enumerate(SEED):
            if code not in existing:
                conn.execute(GarduFollowupType.__table__.insert().values(
                    code=code, name=name, suggest_for=suggest, display_order=order, active=True))
        conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
