"""Stage 9c-fix: end-to-end SQL filtering against multiple measurement rows.

Uses the isolated SQLite API fixture; never touches user's production data.
"""
from io import BytesIO
import warnings
from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.exc import SAWarning
from test_stage4a_units import site, as_unit
from test_stage9a_substations import master, visit
from app.modules.substations.analysis_migrations import run
from app.modules.substations.models_calc import GarduCalcMatch, GarduCalcRule
from app.modules.substations.models import SubstationMeasurement

BASE = '/api/substations/analysis'


def seeded(site):
    client, Session, admin, units = site
    header = as_unit(admin, units['kp'])
    run(Session.kw['bind'])
    feeder, a = master(client, header)
    b = client.post('/api/substations/master', headers=header, json={
        'code': 'GD002', 'name': 'Gardu B', 'power_kva': 100,
        'phase': 3, 'line_count': 2, 'feeder_id': feeder,
        'ownership': 'PLN', 'purpose': 'UMUM'})
    assert b.status_code == 200, b.text
    ids = {}
    for gid, code, cases in (
        (a, 'GD001', [('2026-11-01', 0, True),
                       ('2026-11-02', 30, False),
                       ('2026-11-03', 70, False)]),
        (b.json()['id'], 'GD002', [('2026-11-01', None, False),
                                   ('2026-11-02', 0, False),
                                   ('2026-11-03', 90, False)])):
        for day, amps, grounding in cases:
            values = [] if amps is None else [
                {'code': phase, 'line_no': n, 'value': amps / 2}
                for phase in ('I_R', 'I_S', 'I_T') for n in (1, 2)]
            if grounding:
                values.append({'code': 'GROUND_TR', 'line_no': 0, 'flag': 'PUTUS'})
            response = client.put('/api/substations/measurements', headers=header,
                                  json=visit(gid, values=values, day=day))
            assert response.status_code == 200, response.text
            ids[(code, day)] = response.json()['id']
    return client, Session, header, ids


def get(client, header, endpoint, params):
    response = client.get(BASE + endpoint, headers=header, params=params)
    assert response.status_code == 200, response.text
    return response


def test_numeric_every_operator_on_selected_visit_not_first_sqlite(site):
    client, Session, header, mids = seeded(site)
    checks = (
        ('gte', 30, None, {mids['GD001', '2026-11-02'],
                           mids['GD001', '2026-11-03'], mids['GD002', '2026-11-03']}),
        ('lte', 0, None, {mids['GD001', '2026-11-01'], mids['GD002', '2026-11-02']}),
        ('antara', 20, 75, {mids['GD001', '2026-11-02'], mids['GD001', '2026-11-03']}),
        ('kosong', None, None, {mids['GD002', '2026-11-01']}),
        ('ada', None, None, set(mids.values()) - {mids['GD002', '2026-11-01']}),
    )
    for op, low, high, expected in checks:
        params = {'mode': 'semua', 'numeric_code': 'total_r', 'numeric_op': op}
        if low is not None: params['numeric_min'] = low
        if high is not None: params['numeric_max'] = high
        with warnings.catch_warnings():
            warnings.simplefilter('error', SAWarning)
            result = get(client, header, '/rows', params).json()
        assert {r['measurement_id'] for r in result['items']} == expected, op
        assert result['total'] == len(expected)
        assert get(client, header, '/summary', params).json()['total'] == len(expected)
        export = get(client, header, '/export', {**params, 'format': 'xlsx',
                                                  'columns': 'code,total_r'})
        book = load_workbook(BytesIO(export.content))
        assert book.active.max_row == len(expected) + 1
        assert 'Keterangan' in book.sheetnames
    # Regression: selecting the most recent visit must use *its* value.
    current = get(client, header, '/rows', {'numeric_code': 'total_r',
                                            'numeric_op': 'gte', 'numeric_min': 80}).json()
    assert {r['measurement_id'] for r in current['items']} == {
        mids['GD002', '2026-11-03']}
    # A zero belongs in >=0 and <=0, NULL never does.
    assert get(client, header, '/rows', {'mode': 'semua', 'numeric_code': 'total_r',
        'numeric_op': 'gte', 'numeric_min': 0}).json()['total'] == 5


def test_numeric_invalid_requests_are_422_on_all_endpoints(site):
    client, _, header, _ = seeded(site)
    invalid = (
        {'numeric_code': 'total_r', 'numeric_op': 'nonsense'},
        {'numeric_code': 'total_r', 'numeric_op': 'gte'},
        {'numeric_code': 'total_r', 'numeric_op': 'lte'},
        {'numeric_code': 'total_r', 'numeric_op': 'antara', 'numeric_min': 0},
        {'numeric_code': 'total_r', 'numeric_op': 'antara',
         'numeric_min': 10, 'numeric_max': 5},
        {'numeric_op': 'ada'},
        {'numeric_code': 'unknown', 'numeric_op': 'kosong'},
    )
    for path in ('/rows', '/summary', '/export'):
        for params in invalid:
            resp = client.get(BASE + path, params=params, headers=header)
            assert resp.status_code == 422, (path, params, resp.text)


def test_findings_repeated_comma_any_all_match_stored_rows(site):
    client, Session, header, mids = seeded(site)
    with Session() as db:
        matches = db.execute(select(GarduCalcMatch.measurement_id, GarduCalcRule.code)
            .join(GarduCalcRule, GarduCalcRule.id == GarduCalcMatch.rule_id)
            .where(GarduCalcRule.kind == 'finding')).all()
    by_id = {mid: {code for rid, code in matches if rid == mid} for mid in mids.values()}
    for selected, mode in ((['kandidat_mutasi'], 'any'),
                           (['kandidat_mutasi', 'grounding'], 'any'),
                           (['kandidat_mutasi', 'grounding'], 'all')):
        expected = {mid for mid, codes in by_id.items()
                    if (any(x in codes for x in selected) if mode == 'any'
                        else all(x in codes for x in selected))}
        params = [('mode', 'semua'), ('finding_mode', mode)] + [
            ('findings', code) for code in selected]
        rows = get(client, header, '/rows', params).json()
        assert {r['measurement_id'] for r in rows['items']} == expected
        assert get(client, header, '/summary', params).json()['total'] == len(expected)
        csv_resp = get(client, header, '/export', params + [('format', 'csv')])
        # Exactly those measurement IDs are exported, with one provenance block.
        assert csv_resp.content.count(b'GD00') == len(expected)
    repeat = get(client, header, '/rows', [('mode','semua'),
        ('findings','kandidat_mutasi,grounding'),('finding_mode','all')]).json()
    assert {r['measurement_id'] for r in repeat['items']} == {
        mid for mid, codes in by_id.items() if {'kandidat_mutasi','grounding'} <= codes}
    for path in ('/rows','/summary','/export'):
        assert client.get(BASE + path, headers=header, params={
            'findings':'nope'}).status_code == 422
    combo = get(client, header, '/rows', [('mode','semua'), ('session','SIANG'),
        ('category','underload'), ('findings','kandidat_mutasi'),
        ('numeric_code','total_r'), ('numeric_op','lte'), ('numeric_min','0'),
        ('sort','total_r'), ('desc','true')]).json()
    assert {r['measurement_id'] for r in combo['items']} == {
        mids['GD001','2026-11-01'], mids['GD002','2026-11-02']}


def test_custom_column_is_filterable_without_code_changes(site):
    client, Session, header, mids = seeded(site)
    created = client.post('/api/substations/calculations/column', headers=header, json={
        'code':'uji_kustom_nilai','name':'Uji kustom nilai','unit':'A',
        'decimals':1,'expression':'total_r * 2','empty_mode':'batal'})
    assert created.status_code == 200, created.text
    for _ in range(10):
        done = client.post('/api/substations/calculations/recalculate?limit=20',
                           headers=header)
        assert done.status_code == 200, done.text
        if done.json()['remaining'] == 0: break
    params = {'mode':'semua','numeric_code':'uji_kustom_nilai',
              'numeric_op':'gte','numeric_min':140}
    data = get(client, header, '/rows', params).json()
    assert {r['measurement_id'] for r in data['items']} == {
        mids['GD001', '2026-11-03'], mids['GD002', '2026-11-03']}
    assert get(client, header, '/summary', params).json()['total'] == 2
    assert get(client, header, '/rows', {**params, 'sort':'uji_kustom_nilai'}).status_code == 200


def test_postgresql_sql_dialect_compiles_correlated_exists(site):
    """Compiler check only: this is NOT an executed PostgreSQL 16 integration test."""
    from sqlalchemy.dialects import postgresql
    from app.db import User
    from app.modules.org_units.models import OrgUnit
    from app.modules.org_units.context import UnitContext
    from app.modules.substations.analysis_queries import filtered
    from app.modules.substations.analysis_router import AnalysisOptions
    client, Session, header, mids = seeded(site)
    with Session() as db:
        unit_id = int(header['X-Unit-Id'])
        ctx = UnitContext(db.get(OrgUnit, unit_id),
                          db.query(User).filter_by(username='admin').one(),
                          frozenset(), True)
        options = AnalysisOptions(mode='semua', numeric_code='total_r',
                                  numeric_op='gte', numeric_min=0)
        sql = str(filtered(db, ctx, options).statement.compile(
            dialect=postgresql.dialect(), compile_kwargs={'literal_binds':True}))
        assert 'EXISTS (SELECT' in sql and 'gardu_calc_values' in sql
        assert 'measurement_id = anon_' in sql and 'value >= 0' in sql
