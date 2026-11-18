"""Stage 9b additive idempotent migration; data seed runs exactly once."""
from sqlalchemy import select
from ..formulas.models import SchemaMigration
from .models_calc import (GarduCalcColumn, GarduCalcConstant, GarduCalcRule,
    GarduCalcHistory, GarduCalcSettings, GarduCalcValue, GarduCalcMatch, GarduCalcMark)
from .calculation_seed import COLUMNS, CONSTANTS, RULES, OLD_EXCEL

VERSION = '20261117_18_stage9b_gardu_calculations'
TABLES = (GarduCalcColumn, GarduCalcConstant, GarduCalcRule, GarduCalcHistory,
          GarduCalcSettings, GarduCalcValue, GarduCalcMatch, GarduCalcMark)


def run(engine):
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        for cls in TABLES:
            cls.__table__.create(conn, checkfirst=True)
        if conn.execute(select(SchemaMigration.version).where(
                SchemaMigration.version == VERSION)).first():
            return
        for code, name, value, unit in CONSTANTS:
            conn.execute(GarduCalcConstant.__table__.insert().values(
                code=code, name=name, value=value, unit=unit, active=True))
        for order, (code, name, unit, expression) in enumerate(COLUMNS):
            description = ('Rumus Excel lama (referensi, bukan rumus baku): ' + OLD_EXCEL
                           if code == 'arus_nominal' else 'Rumus awal sementara; konfirmasi teknis sebelum dipakai untuk keputusan.')
            defaults = dict(name=name, unit=unit, decimals=1, expression=expression,
                            empty_mode='batal', description=description,
                            display_order=order, active=True)
            conn.execute(GarduCalcColumn.__table__.insert().values(
                code=code, origin='default', default_expression=expression,
                default_snapshot=defaults, **defaults))
        for order, (code, name, kind, expression, color, marker) in enumerate(RULES):
            conn.execute(GarduCalcRule.__table__.insert().values(
                code=code, name=name, kind=kind, group_name='Pembebanan' if kind=='category'
                else 'Temuan', expression=expression, color=color, marker=marker,
                display_order=order, active=True, origin='default'))
        conn.execute(GarduCalcSettings.__table__.insert().values(
            id=1, version=1, stale_days=180, pending=True))
        conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
