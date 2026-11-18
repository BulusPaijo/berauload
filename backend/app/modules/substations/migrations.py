"""Stage 9a additive, repeatable schema migration with one-time seeds."""
from sqlalchemy import select
from ..formulas.models import SchemaMigration
from .models import (Substation, SubstationFeeder, SubstationChoice, SubstationParam,
                     SubstationSession, SubstationValueFlag, SubstationField,
                     SubstationMeasurement, SubstationValue, SubstationMasterHistory)

VERSION = '20261117_17_stage9a_substations'
TABLES = (SubstationFeeder, SubstationChoice, Substation, SubstationParam,
          SubstationSession, SubstationValueFlag, SubstationField,
          SubstationMeasurement, SubstationValue, SubstationMasterHistory)
PARAMS = (
    ('I_R', 'Arus R', 'A', 'line'), ('I_S', 'Arus S', 'A', 'line'),
    ('I_T', 'Arus T', 'A', 'line'), ('I_N', 'Arus Netral', 'A', 'line'),
    ('V_R0', 'Tegangan Rel R-0', 'V', 'substation'),
    ('V_S0', 'Tegangan Rel S-0', 'V', 'substation'),
    ('V_T0', 'Tegangan Rel T-0', 'V', 'substation'),
    ('V_RS', 'Tegangan Rel R-S', 'V', 'substation'),
    ('V_ST', 'Tegangan Rel S-T', 'V', 'substation'),
    ('V_TR', 'Tegangan Rel T-R', 'V', 'substation'),
    ('V_END_RN', 'Tegangan Ujung JTR R-N', 'V', 'substation'),
    ('V_END_SN', 'Tegangan Ujung JTR S-N', 'V', 'substation'),
    ('V_END_TN', 'Tegangan Ujung JTR T-N', 'V', 'substation'),
    ('GROUND_TR', 'Grounding Trafo', 'ohm', 'substation'),
    ('GROUND_AR', 'Grounding Arrester', 'ohm', 'substation'),
)


def run(engine):
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        for model in TABLES:
            model.__table__.create(conn, checkfirst=True)
        if conn.execute(select(SchemaMigration.version).where(
                SchemaMigration.version == VERSION)).first():
            return
        for order, (code, name, unit, scope) in enumerate(PARAMS):
            conn.execute(SubstationParam.__table__.insert().values(
                code=code, name=name, unit=unit, scope=scope,
                value_type='number', display_order=order, active=True, required=False,
                min_value=0))
        for order, (code, name) in enumerate((('SIANG', 'Siang'), ('MALAM', 'Malam'))):
            conn.execute(SubstationSession.__table__.insert().values(
                code=code, name=name, display_order=order))
        for order, code in enumerate(('PUTUS', 'TIDAK_TERUKUR', 'TIDAK_ADA')):
            conn.execute(SubstationValueFlag.__table__.insert().values(
                code=code, name=code.replace('_', ' ').title(), display_order=order))
        for kind, codes in (('ownership', ('PLN', 'PEMDA')),
                            ('purpose', ('UMUM', 'KHUSUS'))):
            for i, code in enumerate(codes):
                conn.execute(SubstationChoice.__table__.insert().values(
                    kind=kind, code=code, name=code.title(), display_order=i))
        conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
