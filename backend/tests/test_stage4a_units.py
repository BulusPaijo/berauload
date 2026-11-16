"""Stage 4a cross-unit security and status tests; isolated SQLite synthetic data."""
import os
from datetime import date
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import main
from app.db import (get_db, User, Metric, Asset, Reading, HourRecord, DayState,
                    AuditLog)
from app.security import hash_password
from app.modules.org_units.models import OrgUnit, UserUnitAccess, UnitDayState
from app.modules.org_units.repository import home_unit, root

PASSWORD = 'Unit-Scope-QA-Password-2026'


def login(client, username, password=PASSWORD):
    response = client.post('/api/auth/login', json={'username': username,
                                                     'password': password})
    assert response.status_code == 200, response.text
    return {'X-CSRF-Token': response.json()['csrf']}


@pytest.fixture
def site(tmp_path, monkeypatch):
    engine = create_engine('sqlite:///'+str(tmp_path/'stage4a.db'),
                           connect_args={'check_same_thread': False})
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(main, 'engine', engine)
    monkeypatch.setattr(main, 'SessionLocal', Session)
    monkeypatch.setattr(main, 'UPLOAD_DIR', tmp_path/'uploads')
    monkeypatch.setattr(main, 'STAGING_DIR', tmp_path/'uploads'/'staging')
    monkeypatch.setenv('ADMIN_PASSWORD', PASSWORD)

    def override_db():
        with Session() as db:
            yield db
    main.app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(main.app) as admin:
            ah = login(admin, 'admin')
            with Session() as db:
                top, home = root(db), home_unit(db)
                other = OrgUnit(code='ulp_synthetic', name='ULP Sintetis', level='ulp',
                                parent_id=top.id, active=True)
                db.add(other);db.flush()
                kp = OrgUnit(code='kp_synthetic', name='KP Sintetis', level='kp',
                             parent_id=other.id, active=True)
                foreign_kp = OrgUnit(code='kp_foreign', name='KP Asing', level='kp',
                                     parent_id=home.id, active=True)
                db.add_all((kp, foreign_kp));db.flush()
                groups = {
                    'operator_u': ('operator', other.id, 'operator'),
                    'verifier_u': ('verifier', other.id, 'verifier'),
                    'operator_kp': ('operator', kp.id, 'operator'),
                    'operator_home': ('operator', home.id, 'operator'),
                    'management_root': ('management', top.id, 'management'),
                }
                for username, (global_role, unit_id, unit_role) in groups.items():
                    user = User(username=username, display_name=username,
                                role=global_role, password_hash=hash_password(PASSWORD))
                    db.add(user);db.flush()
                    db.add(UserUnitAccess(user_id=user.id,unit_id=unit_id,role=unit_role))
                ids={'home':home.id,'other':other.id,'kp':kp.id,
                     'foreign_kp':foreign_kp.id,'root':top.id}
                db.commit()
            for label in ('other','kp','foreign_kp'):
                h={**ah,'X-Unit-Id':str(ids[label])}
                create=admin.post('/api/assets',headers=h,json={
                    'code':f'{label}_asset','name':f'{label} Asset','kind':'pembangkit'})
                assert create.status_code==200,create.text
                metric=admin.post('/api/metrics',headers=h,json={
                    'code':f'{label}_load','name':f'{label} Load','unit':'kW',
                    'group_name':'PEMBANGKIT','asset_id':create.json()['id']})
                assert metric.status_code==200,metric.text
            yield admin, Session, ah, ids
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()


def as_unit(headers, unit_id):
    return {**headers, 'X-Unit-Id':str(unit_id)}


def test_unit_isolation_direct_codes_and_global_hour_slot(site):
    admin, Session, ah, ids=site
    when='2026-11-06'
    for label,value in [('other',0),('kp',17),('foreign_kp',99)]:
        response=admin.put(f'/api/records/{when}/5',headers=as_unit(ah,ids[label]),
                           json={'values':{label+'_load':value}})
        assert response.status_code==200,response.text
    with Session() as db:
        assert db.query(HourRecord).filter_by(day=date.fromisoformat(when),hour=5).count()==1
        assert db.query(Reading).count()>=3
    with TestClient(main.app) as operator:
        op=login(operator,'operator_u')
        own=operator.get(f'/api/records/day?day={when}',headers=as_unit(op,ids['other']))
        assert own.status_code==200
        assert own.json()['hours'][5]['values']=={'other_load':0.0}
        child=operator.get(f'/api/records/day?day={when}',headers=as_unit(op,ids['kp']))
        assert child.json()['hours'][5]['values']=={'kp_load':17.0}
        assert operator.get(f'/api/records/day?day={when}',headers=as_unit(op,ids['foreign_kp'])).status_code==404
        assert operator.get(f'/api/records/day?day={when}',headers=as_unit(op,ids['root'])).status_code==404
        for route in ('/api/analytics?metric=foreign_kp_load&start=2026-11-06&end=2026-11-06',
                      '/api/compare?metric=foreign_kp_load&year_a=2025&year_b=2026',
                      '/api/performance/series?codes=foreign_kp_load&start=2026-11-06&end=2026-11-06'):
            assert operator.get(route,headers=as_unit(op,ids['other'])).status_code==404,route
        assert operator.get('/api/dashboard?year=2026&month=11',headers=as_unit(op,ids['other'])).status_code==200
        assert operator.get('/api/monitoring/capacity-vs-load?start=2026-11-06&end=2026-11-06',headers=as_unit(op,ids['other'])).status_code==200
    with TestClient(main.app) as kpuser:
        kphead=login(kpuser,'operator_kp')
        assert kpuser.get(f'/api/records/day?day={when}',headers=as_unit(kphead,ids['other'])).status_code==404
        assert kpuser.put(f'/api/records/{when}/5',headers=as_unit(kphead,ids['other']),
                          json={'values':{'other_load':90}}).status_code==404
    with TestClient(main.app) as manager:
        mh=login(manager,'management_root')
        assert manager.get(f'/api/records/day?day={when}',headers=as_unit(mh,ids['kp'])).status_code==200
        assert manager.put(f'/api/records/{when}/5',headers=as_unit(mh,ids['kp']),
                           json={'values':{'kp_load':51}}).status_code==403


def test_operator_verifier_global_admin_and_unit_status(site):
    admin, Session, ah, ids=site
    day='2026-11-07'
    with TestClient(main.app) as op:
        headers=login(op,'operator_u')
        assert op.put(f'/api/records/{day}/0',headers=as_unit(headers,ids['kp']),
                      json={'values':{'kp_load':0}}).status_code==200
        assert op.post(f'/api/days/{day}/verify',headers=as_unit(headers,ids['kp']),
                       json={'reason':'Disetujui QA'}).status_code==403
        assert op.put(f'/api/records/{day}/0',headers=as_unit(headers,ids['other']),
                      json={'values':{'other_load':33}}).status_code==200
    with TestClient(main.app) as ver:
        vh=login(ver,'verifier_u')
        assert ver.post(f'/api/days/{day}/verify',headers=as_unit(vh,ids['other']),
                        json={'reason':'Sudah diperiksa'}).status_code==200
        assert ver.post(f'/api/days/{day}/verify',headers=as_unit(vh,ids['kp']),
                        json={'reason':'Sudah diperiksa'}).status_code==200
        assert ver.post(f'/api/days/{day}/finalize-tree',headers=as_unit(vh,ids['other']),
                        json={'reason':'Final sesuai catatan'}).status_code==200
        assert ver.post(f'/api/days/{day}/reopen',headers=as_unit(vh,ids['kp']),
                        json={'reason':'Koreksi QA'}).status_code==403
    with Session() as db:
        assert db.query(UnitDayState).filter(UnitDayState.day==date.fromisoformat(day),
                   UnitDayState.unit_id.in_([ids['other'],ids['kp']]),
                   UnitDayState.status=='final').count()==2
        assert db.get(DayState,date.fromisoformat(day)) is None
    assert admin.post(f'/api/days/{day}/reopen',headers=as_unit(ah,ids['kp']),
                      json={'reason':'Dibuka admin'}).status_code==200
    with Session() as db:
        row=db.query(AuditLog).filter_by(action='day_reopen').order_by(AuditLog.id.desc()).first()
        assert row.detail['unit_id']==ids['kp']
        assert row.detail['actor_role']=='admin_global'
    assert admin.put(f'/api/records/{day}/3',headers=as_unit(ah,ids['root']),
                     json={'values':{'kp_load':3}}).status_code==422
    assert admin.post(f'/api/assets',headers=as_unit(ah,ids['root']),
                      json={'code':'bad_root_asset','name':'Root asset','kind':'pembangkit'}).status_code==422
    assert admin.post(f'/api/metrics',headers=as_unit(ah,ids['root']),
                      json={'code':'bad_root_metric','name':'Root metric','unit':'kW',
                            'group_name':'PEMBANGKIT'}).status_code==422
    assert admin.post(f'/api/days/{day}/verify',headers=as_unit(ah,ids['root']),
                      json={'reason':'Root bad'}).status_code==422


def test_bulk_operation_skips_unready_child_and_audits_processed_unit(site):
    admin, Session, ah, ids = site
    day = '2026-11-08'
    assert admin.put(f'/api/records/{day}/0', headers=as_unit(ah, ids['other']),
                     json={'values': {'other_load': 13}}).status_code == 200
    preview = admin.get(f'/api/days/{day}/tree-preview?action=verify',
                        headers=as_unit(ah, ids['other']))
    assert preview.status_code == 200
    assert {r['unit_code']: r['result'] for r in preview.json()['units']} == {
        'ulp_synthetic': 'diproses', 'kp_synthetic': 'dilewati'}
    result = admin.post(f'/api/days/{day}/verify-tree', headers=as_unit(ah, ids['other']),
                        json={'reason': 'Massal parsial'})
    assert result.status_code == 200, result.text
    assert {r['unit_code']: r['result'] for r in result.json()['units']} == {
        'ulp_synthetic': 'diproses', 'kp_synthetic': 'dilewati'}
    with Session() as db:
        assert db.query(UnitDayState).filter_by(day=date.fromisoformat(day),status='verified').count() == 1
        assert db.query(AuditLog).filter_by(action='day_verify',target=day).count() == 1
    nothing = admin.post(f'/api/days/{day}/verify-tree', headers=as_unit(ah, ids['other']),
                         json={'reason': 'Massal tak ada'})
    assert nothing.status_code == 422
    assert 'tanpa data' in nothing.text
    assert admin.put(f'/api/records/{day}/0', headers=as_unit(ah, ids['kp']),
                     json={'values': {'kp_load': 22}}).status_code == 200
    verified = admin.post(f'/api/days/{day}/verify-tree', headers=as_unit(ah, ids['other']),
                          json={'reason': 'KP baru ada'})
    assert verified.status_code == 200
    assert verified.json()['units'][0]['result'] == 'dilewati'
    assert verified.json()['units'][1]['result'] == 'diproses'
    final = admin.post(f'/api/days/{day}/finalize-tree',headers=as_unit(ah,ids['other']),
                       json={'reason':'Semua siap'})
    assert final.status_code == 200
    with Session() as db:
        assert db.query(UnitDayState).filter_by(day=date.fromisoformat(day),status='final').count() == 2
        assert db.query(AuditLog).filter_by(action='day_finalize',target=day).count() == 2


def test_unit_catalog_scope_and_legacy_config_guard(site):
    admin, Session, ah, ids=site
    assert admin.get('/api/catalog',headers=as_unit(ah,ids['other'])).json()['metrics'][0]['code']=='other_load'
    with TestClient(main.app) as kp:
        h=login(kp,'operator_kp')
        assert kp.get('/api/catalog',headers=as_unit(h,ids['kp'])).json()['assets'][0]['code']=='kp_asset'
        assert kp.get('/api/topology').status_code==200 and kp.get('/api/topology').json()==[]
        assert kp.get('/api/historical-calculations').status_code==200 and kp.get('/api/historical-calculations').json()==[]
        assert kp.get('/api/template-import/config').status_code==200
        assert kp.get('/api/template-import/history').json()==[]
        assert kp.get('/api/records/day?day=2026-11-01').status_code==200
        assert kp.post('/api/org-units',headers=h,json={
            'code':'kp_bad','name':'No','level':'ulp','parent_id':ids['root']}).status_code==403
    with Session() as db:
        root_codes={m.code for m in db.query(Metric).filter_by(unit_id=ids['root'])}
        assert all(db.query(Asset).filter_by(unit_id=ids['root']).count()==0 for _ in [0])
        assert not root_codes or all(db.query(Metric).filter_by(code=c).one().input_mode=='computed' for c in root_codes)


def test_stage4c_explicit_grants_multiunit_and_revocation(site):
    admin, Session, ah, ids = site
    request = {'username': 'stage4c_new', 'display_name': 'Pengguna Multi Unit',
               'password': PASSWORD, 'role': 'operator'}
    rejected = admin.post('/api/users', headers=ah, json=request)
    assert rejected.status_code == 422
    assert 'eksplisit' in rejected.text
    bad = admin.post('/api/users', headers=ah, json={**request, 'accesses': [
        {'unit_id': 999999, 'role': 'operator'}]})
    assert bad.status_code == 422
    grants = [{'unit_id': ids['other'], 'role': 'operator'},
              {'unit_id': ids['foreign_kp'], 'role': 'verifier'}]
    created = admin.post('/api/users', headers=ah, json={**request, 'accesses': grants})
    assert created.status_code == 200, created.text
    user_id = created.json()['id']
    with Session() as db:
        rows = db.query(UserUnitAccess).filter_by(user_id=user_id).all()
        assert {(r.unit_id, r.role) for r in rows} == {
            (ids['other'], 'operator'), (ids['foreign_kp'], 'verifier')}
    with TestClient(main.app) as new_client:
        head = login(new_client, request['username'])
        own = new_client.get('/api/org-units')
        assert own.status_code == 200
        def walk(rows):
            return [u['id'] for row in rows for u in [row] + [
                nested for nested in rows_flat(row.get('children', []))]]
        def rows_flat(rows):
            return [unit for row in rows for unit in [row, *rows_flat(row['children'])]]
        ids_seen = {row['id'] for row in rows_flat(own.json())}
        assert ids['root'] not in ids_seen
        assert ids['home'] not in ids_seen
        assert ids['other'] in ids_seen
        assert ids['kp'] in ids_seen
        assert ids['foreign_kp'] in ids_seen
        # Grant at a KP does not expose its ULP parent.
        assert new_client.get('/api/records/day?day=2026-11-07',
                              headers=as_unit(head, ids['home'])).status_code == 404
    before = admin.get(f"/api/org-units/{ids['foreign_kp']}/access", headers=ah).json()
    retained = [row for row in before if row['user_id'] != user_id]
    assert admin.put(f"/api/org-units/{ids['foreign_kp']}/access", headers=ah,
                     json={'entries': retained}).status_code == 200
    with Session() as db:
        assert db.query(UserUnitAccess).filter_by(user_id=user_id).count() == 1


def test_stage4c_readonly_personal_scope_fallback_survives_restart(site):
    from app.modules.dashboard_settings.models import DashboardChartSettings
    from app.modules.standard_reports.models import StandardReportSelection
    from app.modules.dashboard_settings.repository import get_settings
    from app.modules.standard_reports.router import resolve
    admin, Session, ah, ids = site
    with Session() as db:
        actor = db.query(User).filter_by(username='operator_u').one()
        db.add(DashboardChartSettings(unit_id=ids['other'], scope='user',
                                       owner_id=actor.id, metric_codes=['other_load']))
        db.add(StandardReportSelection(unit_id=ids['other'], scope='user',
                                       owner_id=actor.id, metric_code='other_load',
                                       aggregation='max'))
        db.commit()
        assert get_settings(db, 'user', actor.id, ids['other']).metric_codes == ['other_load']
        assert resolve(db, actor.id, ids['other'])['personal']['metric_code'] == 'other_load'
        baseline = (db.query(DashboardChartSettings).count(),
                    db.query(StandardReportSelection).count(),
                    [(x.id, x.scope, x.unit_id) for x in db.query(DashboardChartSettings).all()])
    main.setup()
    main.setup()
    with Session() as db:
        assert (db.query(DashboardChartSettings).count(),
                db.query(StandardReportSelection).count(),
                [(x.id, x.scope, x.unit_id) for x in db.query(DashboardChartSettings).all()]) == baseline
        assert get_settings(db, 'user', actor.id, ids['other']).scope == 'user'


def test_stage4c_selectable_tree_admin_verifier_and_kp(site):
    admin, Session, ah, ids = site
    selectable = admin.get('/api/org-units/selectable')
    assert selectable.status_code == 200
    def flattened(nodes):
        return [item for node in nodes for item in [node, *flattened(node['children'])]]
    assert all(row['active'] for row in flattened(selectable.json()))
    assert ids['other'] in {item['id'] for item in flattened(selectable.json())}
    with TestClient(main.app) as kp:
        login(kp, 'operator_kp')
        rows = flattened(kp.get('/api/org-units/selectable').json())
        assert {item['id'] for item in rows} == {ids['kp']}
    with TestClient(main.app) as verifier:
        vh = login(verifier, 'verifier_u')
        rows = flattened(verifier.get('/api/org-units/selectable').json())
        assert {item['id'] for item in rows} == {ids['other'], ids['kp']}
        assert ids['home'] not in {item['id'] for item in rows}
        assert verifier.get('/api/days/2026-11-12/tree-preview?action=verify',
                            headers=as_unit(vh, ids['home'])).status_code == 404
    with TestClient(main.app) as operator:
        oh = login(operator, 'operator_u')
        assert operator.get('/api/days/2026-11-12/tree-preview?action=verify',
                            headers=as_unit(oh, ids['other'])).status_code == 403
        assert operator.post('/api/days/2026-11-12/verify-tree',
                             headers=as_unit(oh, ids['other']),
                             json={'reason':'Tidak boleh'}).status_code == 403
