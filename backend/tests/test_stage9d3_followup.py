"""Stage 9d-3: follow-ups, monitoring coverage, reports, worksheets."""
import io
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from app import main
from app.db import AuditLog
from app.modules.formulas.models import SchemaMigration
from app.modules.substations.followup_migrations import VERSION, run
from app.modules.substations.followup_models import GarduFollowup, GarduFollowupType
from test_stage4a_units import site, login, as_unit
from test_stage9a_substations import master, visit

F = '/api/substations/followups'
M = '/api/substations/monitoring'


def seed(client, h):
    feeder, first = master(client, h)
    rec = client.put('/api/substations/measurements', headers=h, json=visit(first, values=[
        {'code': 'I_R', 'line_no': 1, 'value': 300}, {'code': 'I_S', 'line_no': 1, 'value': 20},
        {'code': 'I_T', 'line_no': 1, 'value': 20}]))
    assert rec.status_code == 200, rec.text
    second = client.post('/api/substations/master', headers=h, json={
        'code': 'GD002', 'name': 'Belum', 'power_kva': 50, 'phase': 3, 'line_count': 2,
        'feeder_id': feeder, 'ownership': 'PLN', 'purpose': 'UMUM'}).json()['id']
    return first, second, rec.json()['measurement']['id']


def test_migration_seed_once_and_admin_edit_survives(site):
    client, Session, admin, units = site
    engine = Session.kw['bind']
    run(engine); run(engine)
    with Session() as db:
        assert db.query(SchemaMigration).filter_by(version=VERSION).count() == 1
        assert db.query(GarduFollowupType).count() == 9      # 7 seeded in 9d-3 + tukar_trafo, pindah_beban (9e)
        assert {'penyeimbangan', 'uprating', 'mutasi', 'pecah_beban', 'grounding', 'perbaikan_jtr', 'pantau'} <= {t.code for t in db.query(GarduFollowupType)}
    h = as_unit(admin, units['kp'])
    r = client.post(F + '/types', headers=h, json={'code': 'pantau', 'name': 'Pantau rutin', 'suggest_for': []})
    assert r.status_code == 200
    run(engine)
    assert {t['code']: t['name'] for t in client.get(F + '/types', headers=h).json()}['pantau'] == 'Pantau rutin'
    with TestClient(main.app) as op:
        oh = as_unit(login(op, 'operator_kp'), units['kp'])
        assert op.post(F + '/types', headers=oh, json={'code': 'x', 'name': 'X'}).status_code == 403


def test_followup_lifecycle_rights_audit_no_delete(site):
    client, Session, admin, units = site
    h = as_unit(admin, units['kp'])
    first, second, mid = seed(client, h)
    bad = client.post(F, headers=h, json={'substation_id': first, 'type_code': 'nope'})
    assert bad.status_code == 422
    assert client.post(F, headers=h, json={'substation_id': first, 'type_code': 'uprating', 'priority': 'darurat'}).status_code == 422
    assert client.post(F, headers=h, json={'substation_id': second, 'measurement_id': mid, 'type_code': 'uprating'}).status_code == 422
    made = client.post(F, headers=h, json={'substation_id': first, 'measurement_id': mid, 'type_code': 'uprating',
                                           'note': 'Ganti 200 kVA', 'assignee': 'Regu 2', 'due_on': '2026-12-01', 'priority': 'tinggi'})
    assert made.status_code == 200, made.text
    fid = made.json()['id']
    assert made.json()['type_name'] == 'Uprating trafo' and made.json()['status'] == 'terbuka'
    body = {'substation_id': first, 'type_code': 'uprating', 'status': 'dikerjakan', 'expected_version': 9}
    assert client.patch(f'{F}/{fid}', headers=h, json=body).status_code == 409
    body['expected_version'] = 1
    upd = client.patch(f'{F}/{fid}', headers=h, json=body)
    assert upd.status_code == 200 and upd.json()['version'] == 2
    assert client.delete(f'{F}/{fid}', headers=h).status_code == 405
    rows = client.get('/api/substations/analysis/rows', headers=h).json()['items']
    by = {r['code']: r for r in rows}
    assert by['GD001']['followup']['status'] == 'dikerjakan' and by['GD002']['followup'] is None
    other = client.post(F, headers=h, json={'substation_id': second, 'type_code': 'pantau'}).json()['id']
    bulk = client.post(F + '/bulk', headers=h, json={'ids': [fid, other, 99999], 'status': 'selesai', 'assignee': 'Regu 3'})
    assert bulk.json() == {'updated': 2, 'skipped': [99999]}
    listed = client.get(F, headers=h, params={'status': ['selesai']}).json()
    assert listed['total'] == 2 and listed['counts']['selesai'] == 2
    assert client.get(F, headers=h, params={'status': ['salah']}).status_code == 422
    with TestClient(main.app) as kp:
        kh = login(kp, 'operator_kp')
        assert kp.get(F, headers=as_unit(kh, units['kp'])).json()['total'] == 2
        assert kp.get(F, headers=as_unit(kh, units['home'])).status_code == 404
    with Session() as db:
        assert db.query(AuditLog).filter_by(action='gardu_followup').count() == 5
        assert db.query(GarduFollowup).count() == 2


def test_suggestions_coverage_unmeasured(site):
    client, Session, admin, units = site
    h = as_unit(admin, units['kp'])
    first, second, mid = seed(client, h)
    sug = client.get(f'{F}/suggest/{first}', headers=h).json()
    assert sug['measurement_id'] == mid
    assert all(s['because'] for s in sug['suggestions'])
    with Session() as db:
        assert db.query(GarduFollowup).count() == 0          # suggestions never create rows
    cov = client.get(M + '/coverage', headers=h, params={'start': '2034-01-01', 'end': '2034-01-31'}).json()
    assert cov['total']['total'] == 2 and cov['total']['measured'] == 1 and cov['total']['never'] == 1
    assert cov['total']['percent'] == 50.0
    assert client.get(M + '/coverage', headers=h, params={'start': '2034-02-01', 'end': '2034-01-01'}).status_code == 422
    un = client.get(M + '/unmeasured', headers=h, params={'days': 0}).json()
    assert [i['code'] for i in un['items']][0] == 'GD002' and un['items'][0]['last_measured_on'] is None


def test_report_pdf_xlsx_and_worksheet(site):
    client, Session, admin, units = site
    h = as_unit(admin, units['kp'])
    first, second, mid = seed(client, h)
    client.post(F, headers=h, json={'substation_id': first, 'type_code': 'uprating'})
    x = client.get(M + '/report', headers=h, params={'format': 'xlsx'})
    assert x.status_code == 200, x.text
    wb = load_workbook(io.BytesIO(x.content))
    assert {'Ringkasan', 'Belum diukur', 'Tindak lanjut', 'Ambang dipakai'} <= set(wb.sheetnames)
    tl = list(wb['Tindak lanjut'].iter_rows(values_only=True))
    assert tl[1][0] == 'GD001' and tl[1][2] == 'Uprating trafo'
    p = client.get(M + '/report', headers=h, params={'format': 'pdf'})
    assert p.status_code == 200 and p.content.startswith(b'%PDF')
    assert client.get(M + '/report', headers=h, params={'format': 'doc'}).status_code == 422
    ws = client.post(M + '/worksheet', headers=h, json={'ids': [first, second], 'format': 'xlsx'})
    rows = list(load_workbook(io.BytesIO(ws.content)).active.iter_rows(values_only=True))
    assert rows[1][:2] == ('Kode', 'Nama') and any('(A)' in str(c) for c in rows[1])
    assert sum(1 for r in rows if r[0] == 'GD002' and isinstance(r[6], int)) == 2   # 2 jurusan lines
    wp = client.post(M + '/worksheet', headers=h, json={'ids': [first], 'format': 'pdf'})
    assert wp.content.startswith(b'%PDF')
    assert client.post(M + '/worksheet', headers=h, json={'ids': [first, 999], 'format': 'pdf'}).status_code == 404
