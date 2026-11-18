"""Regression tests for Stage 9a-fix. Synthetic SQLite, no production records."""
from app.db import AuditLog
from app.modules.substations.models import (Substation, SubstationValue,
    SubstationMeasurement, SubstationMasterHistory, SubstationParam)
from test_stage4a_units import site, as_unit
from test_stage9a_substations import master, visit


def create_second(client, headers, code='GD002'):
    response = client.post('/api/substations/master', headers=headers, json={
        'code': code, 'name': 'Gardu kedua', 'power_kva': 50, 'line_count': 2})
    assert response.status_code == 200, response.text
    return response.json()['id']


def test_duplicate_codes_master_atomic_and_feeders(site):
    client, Session, admin, ids = site
    h = as_unit(admin, ids['kp'])
    feeder, first = master(client, h)
    second = create_second(client, h)
    with Session() as db:
        n_audit = db.query(AuditLog).count()
        n_history = db.query(SubstationMasterHistory).count()
    duplicate = client.patch(f'/api/substations/master/{second}', headers=h,
                             json={'code': 'GD001', 'name': 'Should not save'})
    assert duplicate.status_code == 409 and 'Kode gardu sudah dipakai' in duplicate.text
    create = client.post('/api/substations/master', headers=h,
                         json={'code': 'GD001', 'name': 'Duplicate', 'power_kva': 100})
    assert create.status_code == 409
    assert client.post('/api/substations/feeders', headers=h,
                       json={'code': 'FEED1', 'name': 'Duplicate'}).status_code == 409
    assert client.patch(f'/api/substations/feeders/{feeder}', headers=h,
                        json={'code': 'SOMETHING'}).status_code == 409
    with Session() as db:
        assert db.get(Substation, second).code == 'GD002'
        assert db.get(Substation, second).name == 'Gardu kedua'
        assert db.query(SubstationMasterHistory).count() == n_history
        assert db.query(AuditLog).count() == n_audit


def test_line_reduction_requires_explicit_confirm_preserves_measurement(site):
    client, Session, admin, ids = site
    h = as_unit(admin, ids['kp'])
    _, first = master(client, h)
    saved = client.put('/api/substations/measurements', headers=h, json=visit(first, values=[
        {'code': 'I_R', 'line_no': 2, 'value': 0}]))
    assert saved.status_code == 200, saved.text
    denied = client.patch(f'/api/substations/master/{first}', headers=h,
                          json={'line_count': 1})
    assert denied.status_code == 409
    detail = denied.json()['detail']
    assert detail['code'] == 'LINE_REDUCTION_CONFIRM_REQUIRED'
    assert detail['affected_values'] == 1
    with Session() as db:
        assert db.get(Substation, first).line_count == 2
    approved = client.patch(f'/api/substations/master/{first}', headers=h,
                            json={'line_count': 1, 'confirm_line_reduction': True})
    assert approved.status_code == 200, approved.text
    with Session() as db:
        row = db.query(SubstationMeasurement).filter_by(substation_id=first).first()
        assert row.snapshot_line_count == 2
        assert db.query(SubstationValue).filter_by(measurement_id=row.id, line_no=2).first().value == 0
    new = create_second(client, h)
    assert client.patch(f'/api/substations/master/{new}', headers=h,
                        json={'line_count': 1}).status_code == 200


def test_bulk_duplicate_and_reduction_are_isolated(site):
    client, Session, admin, ids = site
    h = as_unit(admin, ids['kp'])
    _, first = master(client, h)
    second = create_second(client, h)
    assert client.put('/api/substations/measurements', headers=h, json=visit(first, values=[
        {'code': 'I_R', 'line_no': 2, 'value': 10}])).status_code == 200
    result = client.patch('/api/substations/master/bulk', headers=h,
                          json={'ids': [first, second], 'changes': {'line_count': 1}})
    assert result.status_code == 200, result.text
    statuses = {r['id']: r['status'] for r in result.json()['results']}
    assert statuses == {first: 'needs_confirmation', second: 'updated'}
    assert client.patch('/api/substations/master/bulk', headers=h,
                        json={'ids': [first], 'changes': {'line_count': 1,
                             'confirm_line_reduction': True}}).json()['results'][0]['status'] == 'updated'
    third = create_second(client, h, 'GD003')
    code = client.patch('/api/substations/master/bulk', headers=h,
                        json={'ids': [second, third], 'changes': {'code': 'SAMECODE'}})
    assert code.status_code == 200
    assert [r['status'] for r in code.json()['results']] == ['updated', 'error']


def test_duplicate_definitions_and_min_max(site):
    client, Session, admin, ids = site
    h = as_unit(admin, ids['kp'])
    with Session() as db:
        param = db.query(SubstationParam).filter_by(code='I_R').first()
        ident = param.id
    assert client.post('/api/substations/definitions/params', headers=h,
                       json={'code': 'I_R', 'name': 'Duplicate'}).status_code == 409
    assert client.patch(f'/api/substations/definitions/params/{ident}', headers=h,
                        json={'code': 'I_S'}).status_code == 409
    assert client.patch(f'/api/substations/definitions/params/{ident}', headers=h,
                        json={'min_value': 25, 'max_value': 10}).status_code == 422
    assert client.patch(f'/api/substations/definitions/params/{ident}', headers=h,
                        json={'max_value': 10}).status_code == 200
    assert client.patch(f'/api/substations/definitions/params/{ident}', headers=h,
                        json={'min_value': 25}).status_code == 422
