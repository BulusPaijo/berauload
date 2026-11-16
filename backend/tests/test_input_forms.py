"""V1.4.2 dynamic form: default parity, customization, ACL, integrity and migration."""
import os
import tempfile
from pathlib import Path

root = Path(tempfile.mkdtemp(prefix='berauload_forms_'))
os.environ['DATABASE_URL'] = 'sqlite:///' + str(root / 'qa.db')
os.environ['UPLOAD_DIR'] = str(root / 'uploads')
os.environ['ADMIN_PASSWORD'] = 'Test-Dynamic-Forms-2026-Strong'

from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal, engine, Metric, Reading, HourRecord
from app.modules.input_forms.migrations import run, VERSION
from app.modules.input_forms.models import InputFormTab, InputFormPlacement, InputFormRevision
from app.modules.formulas.models import SchemaMigration


def login(c, username='admin', password=None):
    r = c.post('/api/auth/login', json={
        'username': username, 'password': password or os.environ['ADMIN_PASSWORD']})
    assert r.status_code == 200, r.text
    return {'X-CSRF-Token': r.json()['csrf']}


def payload(c):
    result = c.get('/api/input-form/config')
    assert result.status_code == 200, result.text
    data = result.json()
    return {'expected_version': data['version'],
            'tabs': [{key: x[key] for key in ('code', 'name', 'active')}
                     for x in data['tabs']],
            'placements': [{key: x[key] for key in ('metric_code', 'tab_code', 'visible')}
                           for x in data['placements']]}


def test_defaults_and_migration_repeat_without_changing_records():
    with TestClient(app) as c:
        head = login(c)
        settings = c.get('/api/input-form/config').json()
        assert [x['code'] for x in settings['tabs']] == [
            'PEMBANGKIT', 'KUALITAS', 'FEEDER', 'REKAP', 'REKAP_LAIN']
        place = {p['metric_code']: p for p in settings['placements']}
        assert place['pltu_lati_cb33_kw']['tab_code'] == 'PEMBANGKIT'
        assert place['feeder_1_r_a']['tab_code'] == 'FEEDER'
        assert place['daya_mampu_sistem_kw']['visible'] is False
        assert place['daya_pasok_pembangkit_kw']['visible'] is True
        response = c.put('/api/records/2026-11-14/10', headers=head,
                         json={'values': {'pltu_lati_cb33_kw': 1250}})
        assert response.status_code == 200, response.text
        with SessionLocal() as db:
            old_rows = db.query(Reading).count()
            old_hours = db.query(HourRecord).count()
        run(engine);run(engine)
        with SessionLocal() as db:
            assert db.query(SchemaMigration).filter_by(version=VERSION).count() == 1
            assert db.query(InputFormTab).count() == 5
            assert db.query(InputFormRevision).count() == 1
            assert db.query(Reading).count() == old_rows
            assert db.query(HourRecord).count() == old_hours
        day = c.get('/api/records/day?day=2026-11-14').json()
        assert day['hours'][10]['values']['pltu_lati_cb33_kw'] == 1250


def test_add_custom_tab_move_and_hide_preserves_measurements():
    with TestClient(app) as c:
        head = login(c)
        state = payload(c)
        state['tabs'].append({'code':'tab_trafo','name':'Transformator','active':True})
        target = next(p for p in state['placements']
                      if p['metric_code']=='pltu_lati_cb33_kw')
        target.update(tab_code='tab_trafo', visible=False)
        result = c.put('/api/input-form/config', headers=head, json=state)
        assert result.status_code == 200, result.text
        assert result.json()['version'] == state['expected_version']+1
        placement = {p['metric_code']:p for p in result.json()['placements']}
        assert placement['pltu_lati_cb33_kw']['tab_code']=='tab_trafo'
        assert placement['pltu_lati_cb33_kw']['visible'] is False
        assert c.put('/api/input-form/config', headers=head, json=state).status_code == 409
        assert c.get('/api/records/day?day=2026-11-14').json()['hours'][10][
               'values']['pltu_lati_cb33_kw'] == 1250
        with SessionLocal() as db:
            assert db.query(Reading).filter(Reading.value==1250).count() >= 1


def test_new_parameter_placed_into_custom_tab_and_scope_is_presentation_only():
    with TestClient(app) as c:
        head = login(c)
        new = c.post('/api/metrics', headers=head, json={
            'code':'daya_trafo_qa_kw', 'name':'Daya Trafo QA', 'unit':'kW',
            'group_name':'KUALITAS', 'input_tab_code':'tab_trafo'})
        assert new.status_code == 200, new.text
        placements = {p['metric_code']:p for p in
                      c.get('/api/input-form/config').json()['placements']}
        assert placements['daya_trafo_qa_kw']['tab_code']=='tab_trafo'
        assert placements['daya_trafo_qa_kw']['visible']
        with SessionLocal() as db:
            metric = db.query(Metric).filter_by(code='daya_trafo_qa_kw').one()
            assert metric.group_name == 'KUALITAS'  # still used by reports / Excel
            assert metric.input_mode == 'input'
        write = c.put('/api/records/2026-11-14/11', headers=head,
                      json={'values': {'daya_trafo_qa_kw': 0}})
        assert write.status_code == 200, write.text
        assert c.get('/api/records/day?day=2026-11-14').json()['hours'][11][
               'values']['daya_trafo_qa_kw'] == 0
        new_bad = c.post('/api/metrics', headers=head, json={
            'code':'daya_invalid_qa_kw','name':'Daya Tidak Valid','unit':'kW',
            'group_name':'REKAP','input_tab_code':'tab_tidak_ada'})
        assert new_bad.status_code == 422


def test_archived_tab_and_validation_rules():
    with TestClient(app) as c:
        head = login(c)
        state = payload(c)
        tab = next(t for t in state['tabs'] if t['code']=='tab_trafo')
        tab['active'] = False
        result = c.put('/api/input-form/config', headers=head, json=state)
        assert result.status_code == 200, result.text
        assert next(t for t in result.json()['tabs'] if t['code']=='tab_trafo')['active'] is False
        bad = payload(c)
        bad['tabs'] = [t for t in bad['tabs'] if t['code']!='tab_trafo']
        assert c.put('/api/input-form/config', headers=head,json=bad).status_code==422
        bad = payload(c)
        bad['tabs'][0]['code']=bad['tabs'][1]['code']
        assert c.put('/api/input-form/config', headers=head,json=bad).status_code==422
        bad = payload(c)
        bad['placements'][0]['tab_code']='unknown_tab'
        assert c.put('/api/input-form/config', headers=head,json=bad).status_code==422
        bad = payload(c)
        bad['tabs'] = [{**t,'active':False} for t in bad['tabs']]
        assert c.put('/api/input-form/config', headers=head,json=bad).status_code==422


def test_permissions_read_for_operator_but_write_admin_only():
    with TestClient(app) as c:
        head = login(c)
        created=c.post('/api/users', headers=head, json={
            'username':'forms_operator_qa','display_name':'Operator Form QA',
            'password':'Operator-Form-Test-2026-Strong','role':'operator', 'accesses': _qa_grants('operator')})
        assert created.status_code == 200, created.text
        with TestClient(app) as operator:
            op = login(operator,'forms_operator_qa','Operator-Form-Test-2026-Strong')
            assert operator.get('/api/input-form/config').status_code == 200
            assert operator.put('/api/input-form/config',headers=op,
                                json=payload(operator)).status_code == 403
        assert c.get('/api/input-form/config').status_code == 200


def _qa_grants(role):
    """Updated synthetic fixture: Stage 4c requires explicit unit grants."""
    from app.modules.org_units.repository import home_unit, root
    with SessionLocal() as db:
        unit = root(db) if role == 'management' else home_unit(db)
        return [{'unit_id': unit.id, 'role': role}]
