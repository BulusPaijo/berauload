"""Stage 9c additive, idempotent; view seed only on first migration."""
from sqlalchemy import select, text
from ..formulas.models import SchemaMigration
from .models_calc import GarduCalcColumn, GarduCalcRule
from .analysis_models import GarduAnalysisView, GarduAnalysisSettings

VERSION = '20261117_19_stage9c_analysis'


def run(engine):
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        for cls in (GarduAnalysisSettings, GarduAnalysisView):
            cls.__table__.create(conn, checkfirst=True)
        for name, table, fields in (
            ('ix_gardu_analysis_measured_date', 'substation_measurements',
             'substation_id, session, measured_on DESC, id DESC'),
            ('ix_gardu_analysis_match_code', 'gardu_calc_matches', 'rule_id, measurement_id'),
        ):
            conn.execute(text(f'CREATE INDEX IF NOT EXISTS {name} ON {table} ({fields})'))
        if conn.execute(select(SchemaMigration.version).where(
                SchemaMigration.version == VERSION)).first(): return
        column = conn.execute(select(GarduCalcColumn.id).where(
            GarduCalcColumn.code == 'persen_beban')).first()
        if column:
            conn.execute(GarduAnalysisSettings.__table__.insert().values(
                id=1, reference_column_id=column[0]))
        for code, name, kind in (
            ('overload', 'Overload', 'category'),
            ('tidak_seimbang', 'Tidak seimbang', 'finding'),
            ('tegangan_drop', 'Tegangan drop', 'finding')):
            found = conn.execute(select(GarduCalcRule.id).where(
                GarduCalcRule.code == code)).first()
            if found:
                layout = {'mode':'terakhir','session':'tertinggi',
                          'category':code if kind == 'category' else '',
                          'findings':[code] if kind == 'finding' else [],
                          'columns':['code','feeder','power_kva','measured_on',
                                     'reference','category','findings']}
                conn.execute(GarduAnalysisView.__table__.insert().values(
                    owner_id=None, name=name, shared=True, is_default=False,
                    layout=layout))
        conn.execute(GarduAnalysisView.__table__.insert().values(
            owner_id=None, name='Belum diukur', shared=True,
            layout={'mode':'terakhir','session':'tertinggi','status':'belum',
                    'columns':['code','feeder','power_kva','measured_on']}))
        conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
