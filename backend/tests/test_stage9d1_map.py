"""Stage 9d1 isolated SQLite security, map selection, and chart reading."""
from fastapi.testclient import TestClient
from sqlalchemy import select
from app import main
from app.db import AuditLog
from app.modules.formulas.models import SchemaMigration
from app.modules.substations.map_migrations import VERSION, run
from app.modules.substations.map_models import GarduTileSettings
from app.modules.substations.models import Substation, SubstationMeasurement
from test_stage4a_units import site, login, as_unit
from test_stage9a_substations import master, visit

BASE = '/api/substations/map'


def test_tiles_admin_audit_csrf_and_migration_twice(site):
    client, Session, admin, units = site
    h = as_unit(admin, units['kp'])
    engine = Session.kw['bind']
    run(engine)
    run(engine)
    with Session() as db:
        assert db.query(SchemaMigration).filter_by(version=VERSION).count() == 1
        assert db.query(GarduTileSettings).count() == 1
    tiles = client.get(BASE+'/tiles', headers=h)
    assert tiles.status_code == 200
    assert 'openstreetmap.org' in tiles.json()['tile_url']
    assert tiles.json()['attribution'] == '© OpenStreetMap contributors'
    assert client.patch(BASE+'/tiles', json={'enabled':False,'tile_url':
        'https://tiles.example.com/{z}/{x}/{y}.png', 'attribution':'Uji'}).status_code in (401,403)
    for url in ('javascript:alert(1)', 'file:///etc/passwd',
                'https://tiles.example.com/z/x/y.png',
                'https://bad.com/\" onerror=alert(1)/{z}/{x}/{y}.png'):
        resp = client.patch(BASE+'/tiles', headers=h, json={
            'enabled':True,'tile_url':url, 'attribution':'Uji'})
        assert resp.status_code == 422, (url,resp.text)
    with TestClient(main.app) as op:
        op_header = login(op, 'operator_u')
        assert op.get(BASE+'/tiles',headers=as_unit(op_header,units['kp'])).status_code == 200
        assert op.patch(BASE+'/tiles',headers=as_unit(op_header,units['kp']), json={
            'enabled':False,'tile_url':tiles.json()['tile_url'],
            'attribution':'Contoh'}).status_code == 403
    saved = client.patch(BASE+'/tiles',headers=h,json={'enabled':False,
        'tile_url':'https://tiles.example.com/{z}/{x}/{y}.png',
        'attribution':'Contoh lisensi ubin'})
    assert saved.status_code == 200, saved.text
    run(engine)
    assert client.get(BASE+'/tiles',headers=h).json()['enabled'] is False
    with Session() as db:
        assert db.query(AuditLog).filter_by(action='gardu_tiles').count() == 1


def test_points_filters_rights_invalid_coordinates_and_no_measurement(site):
    client, Session, admin, units = site
    home = as_unit(admin, units['kp'])
    feeder, first = master(client,home)
    updates = client.patch(f'/api/substations/master/{first}',headers=home,json={
        'lat':2.25,'lon':117.4})
    assert updates.status_code == 200,updates.text
    created = client.post('/api/substations/master', headers=home, json={
        'code':'GD_GEO2','name':'Tanpa koordinat','phase':3,'line_count':2,
        'power_kva':200,'feeder_id':feeder,'ownership':'PLN','purpose':'UMUM'})
    assert created.status_code == 200
    missing = created.json()['id']
    bad = client.post('/api/substations/master', headers=home, json={
        'code':'GD_GEO3','name':'Tidak sah','phase':3,'line_count':2,'power_kva':150,
        'feeder_id':feeder,'ownership':'PLN','purpose':'UMUM'})
    assert bad.status_code == 200
    with Session() as db:
        db.get(Substation,bad.json()['id']).lat=91
        db.get(Substation,bad.json()['id']).lon=117
        db.commit()
    res = client.get(BASE+'/points',headers=home).json()
    assert res['total']==3
    assert [p['id'] for p in res['points']]==[first]
    assert res['missing_coordinates']==2
    assert {x['id'] for x in res['missing']}=={missing,bad.json()['id']}
    assert res['points'][0]['status']=='belum'
    recorded = client.put('/api/substations/measurements',headers=home,json=visit(first,
        day='2026-11-17',values=[{'code':'I_R','line_no':1,'value':0},
                {'code':'I_R','line_no':2,'value':0}]))
    assert recorded.status_code == 200, recorded.text
    result = client.get(BASE+'/points',headers=home,params={
        'numeric_code':'total_r','numeric_op':'gte','numeric_min':0,'color_column':'total_r'})
    assert result.status_code == 200, result.text
    assert result.json()['total']==1
    assert result.json()['points'][0]['columns']['total_r']['value']==0
    plain = client.get(BASE+'/points',headers=home).json()['points'][0]
    # 9d-2: slim payload; heavy fields must not return (12 MB regression for 4.5k pins)
    for heavy in ('extra_values','address','brand','sessions','snapshot_power_kva','findings','categories_full'):
        assert heavy not in plain, heavy
    assert plain['columns']=={} and set(plain['category'])=={'code'}
    assert isinstance(plain['finding_codes'],list)
    assert len(str(plain))<700, len(str(plain))
    unknown = client.get(BASE+'/points',headers=home,params={'color_column':'tidak_ada'})
    assert unknown.status_code==200 and unknown.json()['points'][0]['columns']=={}
    assert client.get(BASE+'/points',headers=home,params={
        'numeric_code':'total_r','numeric_op':'gte'}).status_code==422
    assert client.get(BASE+'/points',headers=home,params={
        'findings':'nope'}).status_code==422
    with TestClient(main.app) as kp:
        kp_header=login(kp,'operator_kp')
        good=kp.get(BASE+'/points',headers=as_unit(kp_header,units['kp']))
        assert good.status_code == 200 and good.json()['total']==3
        bad_scope=kp.get(BASE+'/points',headers=as_unit(kp_header,units['home']))
        assert bad_scope.status_code == 404


def test_charts_uses_stored_values_without_mutating_measurements(site):
    client,Session,admin,units=site
    h=as_unit(admin,units['kp'])
    _,first=master(client,h)
    for day,value in [('2026-11-15',30),('2026-11-17',40)]:
        resp=client.put('/api/substations/measurements',headers=h,json=visit(first,
            day=day,values=[{'code':c,'line_no':n,'value':value}
                    for c in ('I_R','I_S','I_T') for n in (1,2)]))
        assert resp.status_code == 200, resp.text
    before=client.get('/api/substations/analysis/rows',headers=h).json()
    data=client.get('/api/substations/analysis/charts',headers=h)
    assert data.status_code == 200, data.text
    payload=data.json()
    assert payload['summary']['total']==1
    assert payload['reference_code']=='persen_beban'
    assert len(payload['pareto'])==1
    # No SQL write occurs while opening points/charts.
    client.get(BASE+'/points',headers=h)
    client.get('/api/substations/analysis/charts',headers=h)
    assert client.get('/api/substations/analysis/rows',headers=h).json()==before
    with Session() as db:
        assert db.query(SubstationMeasurement).count()==2
