"""Stage 7: synthetic SQLite tests of non-destructive PUT and conflict semantics."""
from datetime import date
from app.db import Reading, AuditLog, Metric
from app.modules.records import entry
from test_stage4a_units import site, as_unit, login


def test_disjoint_codes_stay_put_and_noop_has_no_effect(site, monkeypatch):
    client, Session, admin, ids = site
    endpoint = '/api/records/2033-01-02/4'
    h = as_unit(admin, ids['kp'])
    assert client.put(endpoint, headers=h, json={'values':{'kp_load':0}}).status_code == 200
    with Session() as db:
        row = db.query(Reading).join(Metric).filter(Metric.code=='kp_load').first()
        existing = (row.id, float(row.value))
        before_audit = db.query(AuditLog).count()
    called=[]
    monkeypatch.setattr(entry, 'recalculate', lambda *args: called.append(args))
    unchanged = client.put(endpoint, headers=h, json={
        'values':{'kp_load':0},'base':{'kp_load':0}})
    assert unchanged.status_code == 200 and unchanged.json()['unchanged'] is True
    assert called == []
    with Session() as db:
        row = db.query(Reading).join(Metric).filter(Metric.code=='kp_load').first()
        assert (row.id,float(row.value)) == existing
        assert db.query(AuditLog).count() == before_audit
    assert client.put(endpoint, headers=h, json={
        'values':{'kp_load':8},'base':{'kp_load':0}}).status_code == 200
    assert client.get('/api/records/day?day=2033-01-02',headers=h).json()['hours'][4]['values']['kp_load'] == 8


def test_stale_base_returns_409_and_preserves_values(site):
    client, Session, admin, ids = site
    endpoint = '/api/records/2033-02-02/6';h = as_unit(admin, ids['kp'])
    assert client.put(endpoint,headers=h,json={'values':{'kp_load':2}}).status_code==200
    assert client.put(endpoint,headers=h,json={'values':{'kp_load':3},'base':{'kp_load':2}}).status_code==200
    conflict=client.put(endpoint,headers=h,json={'values':{'kp_load':4},'base':{'kp_load':2}})
    assert conflict.status_code==409,conflict.text
    detail=conflict.json()['detail']['conflicts'][0]
    assert detail['kode']=='kp_load'
    assert detail['nilai_anda']==4 and detail['nilai_server']==3
    assert detail['diubah_oleh'] and detail['waktu']
    current=client.get('/api/records/day?day=2033-02-02',headers=h).json()['hours'][6]['values']
    assert current['kp_load']==3
    assert client.put(endpoint,headers=h,json={'values':{'kp_load':4},
       'base':{'kp_load':3},'overrides':['kp_load']}).status_code==200
    with Session() as db:
        log=db.query(AuditLog).filter_by(action='hour_save').order_by(AuditLog.id.desc()).first()
        assert log.detail['overrides']['kp_load']['server_old']==3


def test_other_units_and_locked_day_are_still_protected(site):
    client, Session, admin, ids = site
    url='/api/records/2033-03-03/2';h=as_unit(admin,ids['kp'])
    assert client.put(url,headers=h,json={'values':{'kp_load':8}}).status_code==200
    assert client.post('/api/days/2033-03-03/verify',headers=h,json={'reason':'Test verified'}).status_code==200
    assert client.put(url,headers=h,json={'values':{'kp_load':9}}).status_code==409
    with Session() as db:
        assert db.query(Reading).join(Metric).filter(Metric.code=='kp_load').first().value is not None


def test_two_parameters_same_hour_do_not_erase_others(site):
    client, Session, admin, ids=site
    h=as_unit(admin,ids['kp'])
    metric=client.post('/api/metrics',headers=h,json={
        'code':'stage7_disjoint_metric','name':'Stage7 Disjoint','unit':'kW',
        'group_name':'PEMBANGKIT'})
    assert metric.status_code==200,metric.text
    endpoint='/api/records/2033-04-03/7'
    assert client.put(endpoint,headers=h,json={'values':{'kp_load':17},
           'base':{'kp_load':None}}).status_code==200
    assert client.put(endpoint,headers=h,json={'values':{'stage7_disjoint_metric':0},
           'base':{'stage7_disjoint_metric':None}}).status_code==200
    with Session() as db:
        first=db.query(Reading).join(Metric).filter(Metric.code=='kp_load').first()
        snapshot=(first.id,first.value,first.source)
    assert client.put(endpoint,headers=h,json={'values':{'stage7_disjoint_metric':9},
           'base':{'stage7_disjoint_metric':0}}).status_code==200
    with Session() as db:
        first=db.query(Reading).join(Metric).filter(Metric.code=='kp_load').first()
        assert (first.id,first.value,first.source)==snapshot


def test_recalculation_failure_rolls_back_hour(site,monkeypatch):
    from fastapi.testclient import TestClient
    client,Session,admin,ids=site
    h=as_unit(admin,ids['kp'])
    endpoint='/api/records/2033-05-05/5'
    before=client.get('/api/records/day?day=2033-05-05',headers=h).json()['hours'][5]['values']
    def fail(*args):raise RuntimeError('synthetic recalculation failure')
    monkeypatch.setattr(entry,'recalculate',fail)
    try:client.put(endpoint,headers=h,json={'values':{'kp_load':55}})
    except RuntimeError:pass
    else:raise AssertionError('recalculation must fail')
    after=client.get('/api/records/day?day=2033-05-05',headers=h).json()['hours'][5]['values']
    assert before==after
