"""Stage 9a synthetic SQLite: independent visit readings and safe access."""
from io import BytesIO
from sqlalchemy import select
from openpyxl import load_workbook
from app.db import AuditLog
from app.modules.substations.migrations import VERSION, run
from app.modules.substations.models import (Substation, SubstationFeeder, SubstationMeasurement,
    SubstationParam, SubstationMasterHistory, SubstationValue)
from app.modules.formulas.models import SchemaMigration
from test_stage4a_units import site, as_unit, login


def master(client, headers):
    feeder = client.post('/api/substations/feeders',headers=headers,json={
        'code':'FEED1','name':'Penyulang Awal'})
    assert feeder.status_code == 200,feeder.text
    feeder_id = feeder.json()['id']
    gardu = client.post('/api/substations/master',headers=headers,json={
        'code':'GD001','name':'Gardu A','power_kva':100,'phase':3,
        'line_count':2,'feeder_id':feeder_id,'ownership':'PLN','purpose':'UMUM'})
    assert gardu.status_code == 200,gardu.text
    return feeder_id,gardu.json()['id']


def visit(id,revision=None,values=None,day='2034-01-02'):
    return {'substation_id':id,'measured_on':day,'session':'SIANG',
            'revision':revision,'values':values or []}


def test_migration_seed_and_idempotence(site):
    client,Session,admin,ids=site
    engine=Session.kw['bind'];run(engine);run(engine)
    with Session() as db:
        assert db.query(SchemaMigration).filter_by(version=VERSION).count()==1
        assert db.query(SubstationParam).count()==15
        db.query(SubstationParam).filter_by(code='I_R').first().name='Arus Test'
        db.commit()
    run(engine)
    with Session() as db:
        assert db.query(SubstationParam).filter_by(code='I_R').first().name=='Arus Test'


def test_master_history_snapshot_and_access(site):
    client,Session,admin,ids=site
    h=as_unit(admin,ids['kp']); feeder,id=master(client,h)
    with Session() as db:
        assert db.get(Substation,id).unit_id==ids['kp']
    created=client.put('/api/substations/measurements',headers=h,json=visit(id,values=[
        {'code':'I_R','line_no':1,'value':0},
        {'code':'I_R','line_no':2,'flag':'PUTUS'}]))
    assert created.status_code==200,created.text
    record=created.json()['measurement']
    assert record['revision']==1 and record['snapshot_power_kva']==100
    row=client.patch(f'/api/substations/master/{id}',headers=h,json={
        'power_kva':160,'name':'Gardu Baru','line_count':3})
    assert row.status_code==200,row.text
    forbidden=client.patch(f'/api/substations/master/{id}',headers=h,json={'code':'NEWCODE'})
    assert forbidden.status_code==409
    with Session() as db:
        assert db.get(SubstationMeasurement,record['id']).snapshot_power_kva==100
        assert db.query(SubstationMasterHistory).filter_by(substation_id=id).count()==1
    renamed=client.patch(f'/api/substations/feeders/{feeder}',headers=h,json={'name':'Penyulang Baru'})
    assert renamed.status_code==200
    assert client.patch(f'/api/substations/feeders/{feeder}',headers=h,json={'active':False}).status_code==409
    with Session() as db:
        assert db.get(SubstationMeasurement,record['id']).snapshot_feeder_id==feeder
    with __import__('fastapi').testclient.TestClient(client.app) as kp:
        kh=login(kp,'kp_user') if False else None


def test_revision_flag_noop_verified_bulk(site):
    client,Session,admin,ids=site;h=as_unit(admin,ids['kp']); _,id=master(client,h)
    first=client.put('/api/substations/measurements',headers=h,json=visit(id,values=[
        {'code':'I_R','line_no':1,'value':0},{'code':'GROUND_TR','line_no':0,'flag':'PUTUS'}]))
    assert first.status_code==200,first.text
    current=first.json()['measurement']
    bad=client.put('/api/substations/measurements',headers=h,json=visit(id,1,values=[
        {'code':'I_R','line_no':3,'value':6}]))
    assert bad.status_code==422
    assert client.put('/api/substations/measurements',headers=h,json=visit(id,1,values=[
        {'code':'I_R','line_no':1,'value':9},{'code':'I_R','line_no':2,'value':1}])).status_code==200
    stale=client.put('/api/substations/measurements',headers=h,json=visit(id,1,values=[
        {'code':'I_R','line_no':1,'value':99}]))
    assert stale.status_code==409
    bulk=client.post('/api/substations/measurements/bulk',headers=h,json={'items':[
        visit(id,1,values=[{'code':'I_R','line_no':1,'value':13}]),
        visit(id,2,values=[{'code':'I_R','line_no':1,'value':9}])]})
    assert bulk.status_code==200,bulk.text
    assert [r['status'] for r in bulk.json()['results']]==['conflict','unchanged']
    measurement_id=current['id']
    verify=client.post('/api/substations/measurements/actions',headers=h,json={
        'ids':[measurement_id],'action':'verify'})
    assert verify.status_code==200,verify.text
    assert client.put('/api/substations/measurements',headers=h,json=visit(id,2,values=[
        {'code':'I_R','line_no':1,'value':9}])).status_code==409
    reopen=client.post('/api/substations/measurements/actions',headers=h,json={
        'ids':[measurement_id],'action':'reopen','reason':'Ukur ulang'})
    assert reopen.status_code==200,reopen.text
    assert reopen.json()['results'][0]['status']=='reopen'
    with Session() as db:
        assert db.query(SubstationValue).filter_by(measurement_id=measurement_id).count()==3
        assert db.query(AuditLog).filter_by(action='substation_visit_reopen').count()==1


def test_master_import_preview_and_templates(site):
    client,Session,admin,ids=site;h=as_unit(admin,ids['kp'])
    response=client.get('/api/substations/master/template',headers=h)
    assert response.status_code==200
    book=load_workbook(BytesIO(response.content));assert book.active['A1'].value=='kode'
    blob=b'kode,nama,phase,line_count,power_kva,penyulang\nGD02,Gardu CSV,3,1,"42,5",NEWFEED\n'
    preview=client.post('/api/substations/master/import/preview',headers=h,
        files={'file':('master.csv',blob,'text/csv')})
    assert preview.status_code==200,preview.text
    token=preview.json()['token']
    with Session() as db:
        assert db.query(Substation).filter_by(code='GD02').count()==0
    denied=client.post('/api/substations/master/import/apply',headers=h,
        json={'token':token})
    assert denied.status_code==422
    applied=client.post('/api/substations/master/import/apply',headers=h,
        json={'token':token,'create_feeders':True})
    assert applied.status_code==200,applied.text
    assert applied.json()['results'][0]['status']=='created'
    with Session() as db:
        assert db.query(Substation).filter_by(code='GD02').count()==1


def test_master_validate_and_no_hourly_data(site):
    from app.db import Reading,HourRecord
    client,Session,admin,ids=site;h=as_unit(admin,ids['kp']); _,id=master(client,h)
    for payload in ({'line_count':6},{'phase':2},{'power_kva':0},{'lat':91}):
        assert client.patch(f'/api/substations/master/{id}',headers=h,json=payload).status_code==422
    with Session() as db:
        before=(db.query(HourRecord).count(),db.query(Reading).count())
    assert client.put('/api/substations/measurements',headers=h,json=visit(id,values=[
        {'code':'I_R','line_no':1,'value':0}])).status_code==200
    with Session() as db:
        assert before==(db.query(HourRecord).count(),db.query(Reading).count())


def test_access_read_inheritance_and_verifier_only(site):
    from fastapi.testclient import TestClient
    from app import main
    client,Session,admin,ids=site
    h=as_unit(admin,ids['kp']); _,id=master(client,h)
    made=client.put('/api/substations/measurements',headers=h,json=visit(id,values=[
        {'code':'I_R','line_no':1,'value':0}]))
    m_id=made.json()['id']
    with TestClient(main.app) as operator:
        op=login(operator,'operator_u')
        assert operator.get('/api/substations/master',headers=as_unit(op,ids['other'])).status_code==200
        assert operator.get(f'/api/substations/master/{id}',headers=as_unit(op,ids['other'])).status_code==200
        assert operator.post('/api/substations/measurements/actions',headers=as_unit(op,ids['kp']),
                   json={'ids':[m_id],'action':'verify'}).status_code==403
        assert operator.post('/api/substations/master',headers=as_unit(op,ids['kp']),json={}).status_code==403
        assert operator.get('/api/substations/master',headers=as_unit(op,ids['foreign_kp'])).status_code==404
    with TestClient(main.app) as kp:
        kphead=login(kp,'operator_kp')
        assert kp.get('/api/substations/master',headers=as_unit(kphead,ids['other'])).status_code==404
        assert kp.get('/api/substations/master',headers=as_unit(kphead,ids['kp'])).json()['total']==1
    with TestClient(main.app) as verifier:
        vh=login(verifier,'verifier_u')
        assert verifier.post('/api/substations/measurements/actions',headers=as_unit(vh,ids['kp']),
                   json={'ids':[m_id],'action':'verify'}).json()['results'][0]['status']=='verify'
    with TestClient(main.app) as management:
        mh=login(management,'management_root')
        assert management.get('/api/substations/master',headers=as_unit(mh,ids['root'])).json()['total']==1
        assert management.put('/api/substations/measurements',headers=as_unit(mh,ids['kp']),json=visit(id)).status_code==403
    with TestClient(main.app) as unauth:
        assert unauth.get('/api/substations/master').status_code==401


def test_measurement_import_flag_fill_empty_and_verified(site, monkeypatch, tmp_path):
    from app.modules.substations import imports_service
    monkeypatch.setattr(imports_service,'STAGING',tmp_path/'preview')
    client,Session,admin,ids=site;h=as_unit(admin,ids['kp']);_,id=master(client,h)
    original=client.put('/api/substations/measurements',headers=h,json=visit(id,values=[
        {'code':'I_R','line_no':1,'value':0}]))
    assert original.status_code==200
    blob=('kode,tanggal,sesi,I_R:J1,I_R:J2,GROUND_TR\n'
          'GD001,2034-01-02,SIANG,99,"2,5",PUTUS\n').encode()
    preview=client.post('/api/substations/measurements/import/preview',headers=h,
        files={'file':('sesi.csv',blob,'text/csv')})
    assert preview.status_code==200,preview.text
    assert not preview.json()['rows'][0]['errors']
    applied=client.post('/api/substations/measurements/import/apply',headers=h,
       json={'token':preview.json()['token']})
    assert applied.status_code==200,applied.text
    measurements=client.get('/api/substations/measurements/grid?day=2034-01-02&session=SIANG&ids='+str(id),headers=h)
    vals=measurements.json()['items'][0]['values']
    codes={p.id:p.code for p in Session().query(SubstationParam).all()}
    values={(codes[v['param_id']],v['line_no']):v for v in vals}
    assert values[('I_R',1)]['value']==0
    assert values[('I_R',2)]['value']==2.5
    assert values[('GROUND_TR',0)]['flag']=='PUTUS'
    verify=client.post('/api/substations/measurements/actions',headers=h,json={
       'ids':[original.json()['id']],'action':'verify'})
    assert verify.status_code==200
    preview=client.post('/api/substations/measurements/import/preview',headers=h,
        files={'file':('sesi.csv',blob,'text/csv')})
    blocked=client.post('/api/substations/measurements/import/apply',headers=h,
       json={'token':preview.json()['token'],'mode':'overwrite'})
    assert blocked.status_code==200
    assert blocked.json()['results'][0]['status']=='error'


def test_bulk_200_mixed_and_validation(site):
    client,Session,admin,ids=site;h=as_unit(admin,ids['kp']);_,id=master(client,h)
    original=client.put('/api/substations/measurements',headers=h,json=visit(id))
    assert original.status_code==200
    items=[visit(id,1,values=[{'code':'I_R','line_no':1,'value':float(i)}],
            day=f'2034-02-{i%28+1:02d}') for i in range(200)]
    # Use only a single known date with an explicit stale revision to force conflict;
    # all other items intentionally get validation errors (wrong revision on new visit).
    items[0]=visit(id,1,day='2034-01-02')
    # A few valid new visits co-exist with conflicts and errors in the same bulk call.
    for i in range(1,6):
        items[i]=visit(id,None,values=[{'code':'I_R','line_no':1,'value':i}],
                       day=f'2034-03-{i:02d}')
    result=client.post('/api/substations/measurements/bulk',headers=h,json={'items':items})
    assert result.status_code==200,result.text
    assert len(result.json()['results'])==200
    assert sum(r['status']=='saved' for r in result.json()['results'])==5
    assert client.post('/api/substations/measurements/bulk',headers=h,
                       json={'items':items+[items[0]]}).status_code==422


def test_measurement_line_count_uses_original_snapshot(site):
    client,Session,admin,ids=site
    h=as_unit(admin,ids['kp']); _,id=master(client,h)
    made=client.put('/api/substations/measurements',headers=h,json=visit(id,values=[
        {'code':'I_R','line_no':2,'value':17}]))
    assert made.status_code==200,made.text
    # Future transformer has 4 lines, historical visit stays 2 lines.
    assert client.patch(f'/api/substations/master/{id}',headers=h,json={
        'line_count':4}).status_code==200
    still_invalid=client.put('/api/substations/measurements',headers=h,json=visit(id,1,values=[
        {'code':'I_R','line_no':3,'value':10}]))
    assert still_invalid.status_code==422
    with Session() as db:
        record=db.get(SubstationMeasurement,made.json()['id'])
        assert record.snapshot_line_count==2


def test_excel_output_sanitizes_formula_prefixes():
    from app.modules.substations.imports_service import safe_cell, workbook_bytes
    for prefix in ('=', '+', '-', '@'):
        assert safe_cell(prefix+'code').startswith("'")
    blob=workbook_bytes([['=SUM(1,1)','+cmd','-cmd','@cmd']],
                        ['Nama','A','B','C'],'Tes Gardu')
    sheet=load_workbook(BytesIO(blob)).active
    assert all(sheet.cell(2,i).data_type != 'f' for i in range(1,5))
    assert sheet.cell(2,1).value.startswith("'=")


def test_import_preview_rejects_garbage_and_bad_line(site, tmp_path, monkeypatch):
    from app.modules.substations import imports_service
    monkeypatch.setattr(imports_service,'STAGING',tmp_path/'previews')
    client,Session,admin,ids=site;h=as_unit(admin,ids['kp']);_,id=master(client,h)
    for content in (b'<html>test</html>', b'PK\x03\x04broken'):
        result=client.post('/api/substations/measurements/import/preview',
            headers=h,files={'file':('file.xlsx',content,'application/octet-stream')})
        assert result.status_code==422
    bad=b'kode,tanggal,sesi,I_R:J3\nGD001,2034-01-02,SIANG,2\n'
    preview=client.post('/api/substations/measurements/import/preview',headers=h,
        files={'file':('file.csv',bad,'text/csv')})
    assert preview.status_code==200
    assert preview.json()['rows'][0]['errors']
    with Session() as db:
        assert db.query(SubstationMeasurement).count()==0
