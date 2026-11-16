"""Stage 3 synthetic tests, isolated SQLite and no production data."""
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault('ADMIN_PASSWORD', 'BerauLoad-Unit-Role-Test-2026')
from app import main
from app.db import get_db, Metric, Reading, HourRecord, DayState, User, AuditLog
from app.modules.org_units.repository import home_unit
from app.modules.org_units.roles import metric_for_role, main_pair, role_codes
from app.modules.dashboard_builder.service import validate_panels
from fastapi import HTTPException


@pytest.fixture
def service(tmp_path, monkeypatch):
    engine = create_engine('sqlite:///' + str(tmp_path / 'db.sqlite'),
                           connect_args={'check_same_thread': False})
    sessions = sessionmaker(engine, expire_on_commit=False, autoflush=False)
    monkeypatch.setattr(main, 'engine', engine)
    monkeypatch.setattr(main, 'SessionLocal', sessions)
    monkeypatch.setattr(main, 'UPLOAD_DIR', tmp_path / 'uploads')
    monkeypatch.setattr(main, 'STAGING_DIR', tmp_path / 'uploads' / 'staging')
    monkeypatch.setenv('ADMIN_PASSWORD', 'BerauLoad-Unit-Role-Test-2026')
    def get_test_db():
        with sessions() as db:
            yield db
    main.app.dependency_overrides[get_db] = get_test_db
    try:
        with TestClient(main.app) as client:
            res = client.post('/api/auth/login', json={
                'username': 'admin', 'password': 'BerauLoad-Unit-Role-Test-2026'})
            assert res.status_code == 200, res.text
            yield client, sessions, {'X-CSRF-Token':res.json()['csrf']}
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()


def seed_readings(sessions):
    with sessions() as db:
        unit_id = home_unit(db).id
        cap, load = main_pair(db, unit_id)
        ts=datetime(2026,11,10,0,tzinfo=timezone.utc)
        record=HourRecord(day=date(2026,11,10),hour=8,timestamp_utc=ts)
        db.add(record);db.flush()
        db.add(Reading(hour_id=record.id,metric_id=cap.id,value=Decimal('30.5'),source='manual'))
        db.add(Reading(hour_id=record.id,metric_id=load.id,value=Decimal('16.25'),source='manual'))
        for old, prefix in [(cap,'capacity'),(load,'load')]:
            dup=Metric(code=f'role_test_{prefix}',name=f'Role test {prefix}',unit='kW',
                       group_name='REKAP',input_mode='computed',unit_id=unit_id,
                       role_key=None,active=True)
            db.add(dup);db.flush()
            db.add(Reading(hour_id=record.id,metric_id=dup.id,
                           value=Decimal('30.5' if prefix=='capacity' else '16.25'),source='manual'))
        db.commit()
        return unit_id, cap.code, load.code


def test_defaults_follow_roles_and_equivalence(service):
    client,sessions,headers=service
    unit_id,old_cap,old_load=seed_readings(sessions)
    queries=[('/api/dashboard?year=2026&month=11', 'peak_kw'),
             ('/api/monitoring/capacity-vs-load?start=2026-11-10&end=2026-11-10','data'),
             ('/api/compare?year_a=2025&year_b=2026','data'),
             ('/api/analytics?start=2026-11-10&end=2026-11-10','data')]
    before=[client.get(url).json() for url,_ in queries]
    result=client.put('/api/primary-metrics',headers=headers,json={
        'capacity_code':'role_test_capacity','load_code':'role_test_load'})
    assert result.status_code==200,result.text
    assert result.json()['configured']
    assert client.get('/api/catalog').json()['roles']['system.capacity']=='role_test_capacity'
    after=[client.get(url).json() for url,_ in queries]
    for first,second in zip(before,after):
        for key in ('peak_kw','min_kw','avg_kw','readings_count','coverage_pct','daily','data'):
            if key in first and key in second:
                assert first[key]==second[key],key
    with sessions() as db:
        assert metric_for_role(db,unit_id,'system.load').code=='role_test_load'
        assert db.query(Metric).filter_by(code=old_load).one().role_key is None
        assert db.query(Metric).filter_by(code=old_cap).one().role_key is None
        assert db.query(AuditLog).filter_by(action='main_metric_roles_update').count()==1


def test_missing_roles_safe_and_no_write(service):
    client,sessions,headers=service
    seed_readings(sessions)
    r=client.put('/api/primary-metrics',headers=headers,json={
        'capacity_code':None,'load_code':None})
    assert r.status_code==200,r.text
    assert r.json()['configured'] is False
    for endpoint in ('/api/dashboard?year=2026&month=11',
                     '/api/monitoring/capacity-vs-load?start=2026-11-10&end=2026-11-10',
                     '/api/compare?year_a=2025&year_b=2026',
                     '/api/analytics?start=2026-11-10&end=2026-11-10',
                     '/api/standard-reports','/api/dashboard-charts'):
        resp=client.get(endpoint)
        assert resp.status_code==200,(endpoint,resp.text)
        assert resp.json()['configured'] is False,(endpoint,resp.json())
    assert client.get('/api/catalog').json()['roles'].get('system.load') is None
    with sessions() as db:
        assert db.query(Reading).count()==4


def test_main_roles_require_admin_and_csrf(service):
    client,sessions,headers=service
    assert client.put('/api/primary-metrics',json={
        'load_code':None,'capacity_code':None}).status_code==403
    bad=client.put('/api/primary-metrics',headers=headers,json={
        'load_code':'beban_sistem_kw','capacity_code':'beban_sistem_kw'})
    assert bad.status_code==422
    invalid=client.put('/api/primary-metrics',headers=headers,json={
        'load_code':'pltu_lati_cb33_kw','capacity_code':'missing'})
    assert invalid.status_code==422


def test_usage_and_confirmation(service):
    client,sessions,headers=service
    with sessions() as db:
        metric=db.query(Metric).filter_by(code='beban_sistem_kw').one()
        metric_id=metric.id
    usage=client.get(f'/api/metrics/{metric_id}/usage')
    assert usage.status_code==200,usage.text
    assert any(x['category']=='parameter_utama' for x in usage.json()['usage'])
    resp=client.put(f'/api/metrics/{metric_id}',headers=headers,json={
        'name':'Beban Sistem','active':False})
    assert resp.status_code==409
    with sessions() as db:
        assert db.get(Metric,metric_id).active
    allow=client.put(f'/api/metrics/{metric_id}',headers=headers,json={
        'name':'Beban Sistem','active':False,'confirm_disable':True})
    assert allow.status_code==200,allow.text
    with sessions() as db:
        assert db.get(Metric,metric_id).active is False


def test_paired_restrictions_follow_new_codes(service):
    _,sessions,_=service
    unit_id,_,_=seed_readings(sessions)
    with sessions() as db:
        for code,role in [('beban_sistem_kw','system.load'),
                          ('daya_pasok_pembangkit_kw','system.capacity')]:
            db.query(Metric).filter_by(code=code).one().role_key=None
        db.query(Metric).filter_by(code='role_test_load').one().role_key='system.load'
        db.query(Metric).filter_by(code='role_test_capacity').one().role_key='system.capacity'
        db.commit()
    from app.modules.dashboard_builder.visualization import validate_visual
    panel={'id':'t','title':'T','kind':'line','source':'metric',
           'metric_codes':['role_test_capacity','role_test_load'],
           'aggregation':'peak','w':6,'h':2,'source_id':None}
    with pytest.raises(HTTPException):
        validate_panels([panel],{'role_test_capacity':'kW','role_test_load':'kW'},set(),set(),{},
                        ('role_test_capacity','role_test_load'))
    panel['aggregation']='avg'
    assert validate_panels([panel],{'role_test_capacity':'kW','role_test_load':'kW'},set(),set(),{},
                           ('role_test_capacity','role_test_load'))
    panel['kind']='stacked_bar'
    with pytest.raises(HTTPException):
        validate_panels([panel],{'role_test_capacity':'kW','role_test_load':'kW'},set(),set(),{},
                        ('role_test_capacity','role_test_load'))
