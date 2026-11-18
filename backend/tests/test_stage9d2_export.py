"""Stage 9d-2 export builder: columns, shapes, safety, limits, templates, audit."""
import csv
import io
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from app import main
from app.db import AuditLog
from app.modules.formulas.models import SchemaMigration
from app.modules.substations import export_builder
from app.modules.substations.export_migrations import VERSION, run
from app.modules.substations.models_calc import GarduCalcColumn
from test_stage4a_units import site, login, as_unit
from test_stage9a_substations import master, visit

B = '/api/substations/export'


def seed(client, h):
    feeder, first = master(client, h)
    second = client.post('/api/substations/master', headers=h, json={
        'code': 'GD002', 'name': '=HYPERLINK("x")', 'power_kva': 200, 'phase': 3,
        'line_count': 1, 'feeder_id': feeder, 'ownership': 'PLN', 'purpose': 'UMUM'})
    assert second.status_code == 200, second.text
    rec = client.put('/api/substations/measurements', headers=h, json=visit(first, values=[
        {'code': 'I_R', 'line_no': 1, 'value': 120}, {'code': 'I_R', 'line_no': 2, 'flag': 'PUTUS'},
        {'code': 'I_S', 'line_no': 1, 'value': 110}, {'code': 'I_T', 'line_no': 1, 'value': 100}]))
    assert rec.status_code == 200, rec.text
    return first, second.json()['id']


def spec(*keys, **extra):
    return {'columns': [{'key': k} if isinstance(k, str) else k for k in keys], **extra}


def post(client, h, path, spec_, flt=None):
    return client.post(B + path, headers=h, json={'filter': flt or {}, 'spec': spec_})


def test_migration_twice_catalog_and_preview_matches_analysis(site):
    client, Session, admin, units = site
    engine = Session.kw['bind']
    run(engine); run(engine)
    with Session() as db:
        assert db.query(SchemaMigration).filter_by(version=VERSION).count() == 1
    h = as_unit(admin, units['kp'])
    first, second = seed(client, h)
    cat = client.get(B + '/catalog', headers=h).json()
    keys = {c['key'] for c in cat['columns']}
    assert {'code', 'param:I_R:1', 'param:I_R:2', 'calc:total_r', 'category', 'findings',
            'definition_version'} <= keys
    assert any(k.startswith('finding:') for k in keys) and any(k.startswith('sesi:') for k in keys)
    s = spec('code', 'name', {'key': 'param:I_R:1', 'header': 'Arus R J1'}, 'param:I_R:2',
             'param:I_S:2', 'calc:total_r', 'category')
    res = post(client, h, '/preview', s)
    assert res.status_code == 200, res.text
    body = res.json()
    analysis = client.get('/api/substations/analysis/rows', headers=h).json()
    assert body['total'] == analysis['total'] == 2          # same filter relation as Analisa
    assert body['headers'][2] == 'Arus R J1'
    rows = {r[0]: r for r in body['rows']}
    assert rows['GD001'][2] == 120.0 and rows['GD001'][3] == 'PUTUS' and rows['GD001'][4] is None
    stored = {r['code']: r['columns'].get('total_r',{}).get('value') for r in analysis['items']}
    assert rows['GD001'][5] == stored['GD001']      # same stored 9b value as Analisa, no recomputation
    assert rows['GD002'][2] is None and rows['GD002'][5] is None   # empty stays empty, not 0
    assert rows['GD002'][1].startswith("'=")                       # injection neutralized


def test_download_csv_xlsx_long_shape_and_audit(site):
    client, Session, admin, units = site
    h = as_unit(admin, units['kp'])
    first, second = seed(client, h)
    s = spec('code', 'param:I_R:1', {'key': 'calc:total_r', 'header': '=evil'}, format='csv', delimiter=',')
    res = post(client, h, '/download', s)
    assert res.status_code == 200 and 'Export_Gardu' in res.headers['content-disposition']
    assert res.content.startswith(b'\xef\xbb\xbf')
    text = res.content.decode('utf-8-sig')
    table = list(csv.reader(io.StringIO(text)))
    assert table[0] == ['Kode gardu', 'Arus R J1 (A)', "'=evil"]
    assert 'KETERANGAN' in text and 'Versi definisi' in text and 'bukan nol' in text
    x = post(client, h, '/download', spec('code', 'calc:total_r', 'category', format='xlsx'))
    wb = load_workbook(io.BytesIO(x.content))
    assert wb.sheetnames == ['Data Gardu', 'Keterangan']
    assert any('Rumus' in str(r[0]) for r in wb['Keterangan'].iter_rows(values_only=True))
    long = post(client, h, '/download', spec('code', 'name', shape='long', format='csv', delimiter=';'))
    lt = list(csv.reader(io.StringIO(long.content.decode('utf-8-sig')), delimiter=';'))
    assert lt[0][-5:] == ['Parameter', 'Satuan', 'Jurusan', 'Nilai', 'Penanda']
    data = [r for r in lt[1:] if r and r[0] == 'GD001']
    assert len(data) == 4 and [r for r in data if r[-1] == 'PUTUS']
    assert post(client, h, '/preview', spec('code', 'param:I_R:1', shape='long')).status_code == 422
    with Session() as db:
        assert db.query(AuditLog).filter_by(action='gardu_export').count() == 3
        assert all('Nilai' not in str(a.detail) for a in db.query(AuditLog).filter_by(action='gardu_export'))


def test_validation_limits_and_unit_access(site, monkeypatch):
    client, Session, admin, units = site
    h = as_unit(admin, units['kp'])
    seed(client, h)
    assert post(client, h, '/preview', spec('code', 'tidak_ada')).status_code == 422
    assert post(client, h, '/preview', spec('code', 'code')).status_code == 422
    assert post(client, h, '/preview', {'columns': []}).status_code == 422
    assert post(client, h, '/preview', {'columns': [{'key': 'code'}] * 2}).status_code == 422
    many = [{'key': f'param:I_R:{n}'} for n in range(1, 6)] + [{'key': c['key']} for c in
            client.get(B + '/catalog', headers=h).json()['columns']]
    assert post(client, h, '/preview', {'columns': many[:80]}).status_code == 422
    assert post(client, h, '/preview', spec('code', format='pdf')).status_code in (200, 422)
    assert post(client, h, '/download', spec('code', format='pdf')).status_code == 422
    assert post(client, h, '/preview', spec('code'), {'category': 'nope'}).status_code == 422
    assert post(client, h, '/preview', spec('code'), {'sort': 'nope'}).status_code == 422
    monkeypatch.setattr(export_builder, 'MAX_WIDE', 1)
    import app.modules.substations.export_router as router
    monkeypatch.setattr(router, 'MAX_WIDE', 1)
    over = post(client, h, '/download', spec('code'))
    assert over.status_code == 422 and 'dibatasi' in over.text
    assert post(client, h, '/preview', spec('code')).json()['over_limit'] is True
    with TestClient(main.app) as kp:
        kh = login(kp, 'operator_kp')
        ok = kp.post(B + '/preview', headers=as_unit(kh, units['kp']), json={'filter': {}, 'spec': spec('code')})
        assert ok.status_code == 200 and ok.json()['total'] == 2
        bad = kp.post(B + '/preview', headers=as_unit(kh, units['home']), json={'filter': {}, 'spec': spec('code')})
        assert bad.status_code == 404


def test_templates_personal_shared_version_archive_and_warnings(site):
    client, Session, admin, units = site
    h = as_unit(admin, units['kp'])
    seed(client, h)
    s = spec('code', 'calc:total_r')
    mine = client.post(B + '/templates', headers=h, json={'name': 'Rekap', 'spec': s})
    assert mine.status_code == 200 and mine.json()['version'] == 1
    assert client.post(B + '/templates', headers=h, json={'name': 'Rekap', 'spec': s}).status_code == 409
    assert client.post(B + '/templates', headers=h, json={'name': 'Buruk', 'spec': spec('zzz')}).status_code == 422
    tid = mine.json()['id']
    assert client.put(f'{B}/templates/{tid}', headers=h, json={
        'name': 'Rekap', 'spec': s, 'expected_version': 9}).status_code == 409
    upd = client.put(f'{B}/templates/{tid}', headers=h, json={
        'name': 'Rekap 2', 'spec': spec('code'), 'expected_version': 1})
    assert upd.status_code == 200 and upd.json()['version'] == 2
    with TestClient(main.app) as op:
        oh = as_unit(login(op, 'operator_kp'), units['kp'])
        assert op.post(B + '/templates', headers=oh, json={'name': 'Bersama', 'shared': True, 'spec': s}).status_code == 403
        assert op.put(f'{B}/templates/{tid}', headers=oh, json={
            'name': 'X', 'spec': s, 'expected_version': 2}).status_code == 403
        assert op.get(B + '/templates', headers=oh).json() == []
    shared = client.post(B + '/templates', headers=h, json={'name': 'Resmi', 'shared': True,
                         'spec': spec('code', 'calc:total_s')})
    assert shared.status_code == 200
    with TestClient(main.app) as op:
        oh = as_unit(login(op, 'operator_kp'), units['kp'])
        assert [t['name'] for t in op.get(B + '/templates', headers=oh).json()] == ['Resmi']
    with Session() as db:
        db.query(GarduCalcColumn).filter_by(code='total_s').first().active = False
        db.commit()
    listed = {t['name']: t for t in client.get(B + '/templates', headers=h).json()}
    assert listed['Resmi']['warnings'] == ['calc:total_s']
    assert client.post(f'{B}/templates/{tid}/archive', headers=h).status_code == 200
    assert 'Rekap 2' not in {t['name'] for t in client.get(B + '/templates', headers=h).json()}
    assert 'Rekap 2' in {t['name'] for t in client.get(B + '/templates?include_archived=true', headers=h).json()}
    with Session() as db:
        assert db.query(AuditLog).filter_by(action='gardu_export_template').count() >= 4
