"""Stage 4b: schema is additive, data rehoming is one-time and transactional."""
import logging
from sqlalchemy import inspect, select, text
from ..formulas.models import SchemaMigration
from .models import OrgUnit, UserUnitAccess

VERSION = '20261115_16_unit_configuration_stage4b'
# Configuration owners, never measurements or immutable revision snapshots.
CONFIG_TABLES = (
    'input_form_tabs', 'input_form_placements', 'input_form_revision',
    'dashboard_layouts', 'dashboard_chart_settings', 'topology_diagrams',
    'report_templates', 'export_templates', 'standard_report_selections',
    'formula_definitions', 'historical_definitions', 'engineering_rules',
)


def ensure_schema(engine):
    """Before older ORM migrations select columns on legacy tables."""
    from . import configuration_models
    with engine.begin() as conn:
        for model in configuration_models.OWNERS:
            model.__table__.create(conn, checkfirst=True)
        for table in (*CONFIG_TABLES, 'audit_logs'):
            names = {c['name'] for c in inspect(conn).get_columns(table)}
            if 'unit_id' not in names:
                conn.execute(text(f'ALTER TABLE {table} '
                                  'ADD COLUMN unit_id INTEGER REFERENCES org_units(id)'))


def backfill_once(engine):
    """Never repeat data movement on restart; do not populate old audit rows."""
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        if conn.execute(select(SchemaMigration.version).where(
                SchemaMigration.version == VERSION)).first():
            return False
        home = conn.execute(select(OrgUnit.id).where(
            OrgUnit.legacy_home.is_(True))).scalar_one()
        unresolved = 0
        counts = {}
        personal_tables = ('dashboard_layouts', 'dashboard_chart_settings',
                           'report_templates', 'export_templates',
                           'standard_report_selections')
        for table in personal_tables:
            rows = conn.execute(text(f'SELECT id, owner_id FROM {table} '
                                     "WHERE unit_id IS NULL AND scope IN ('user', 'personal', 'mine')"))
            for row_id, user_id in rows:
                accesses = conn.execute(text(
                    'SELECT DISTINCT a.unit_id, o.level FROM user_unit_access a '
                    'JOIN org_units o ON o.id=a.unit_id WHERE a.user_id=:user_id'),
                    {'user_id': user_id}).all()
                # A single non-root assignment determines the working unit.
                # UP3/global or multiple assignments do not establish which unit
                # the historical personal configuration represented.
                if len(accesses) == 1 and accesses[0][1] != 'up3':
                    conn.execute(text(f'UPDATE {table} SET unit_id=:unit_id '
                                      'WHERE id=:id AND unit_id IS NULL'),
                                 {'unit_id': accesses[0][0], 'id': row_id})
                else:
                    unresolved += 1
        for table in CONFIG_TABLES:
            counts[table] = conn.execute(text(
                f'UPDATE {table} SET unit_id=:home WHERE unit_id IS NULL'),
                {'home': home}).rowcount
        conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
    logging.getLogger(__name__).info(
        'Stage4b config backfill complete; legacy_home=%s, rows=%s, '
        'personal scope fallback to legacy_home=%s', home, counts, unresolved)
    return True
