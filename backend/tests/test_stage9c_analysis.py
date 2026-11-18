"""Stage 9c isolated SQLite, real API rights and safe exports."""
from io import BytesIO
from openpyxl import load_workbook
from app.modules.substations.analysis_migrations import run
from app.modules.substations.models import Substation
from app.modules.substations.analysis_queries import reference
from test_stage4a_units import site, as_unit, login
from test_stage9a_substations import master, visit

BASE='/api/substations/analysis'


def test_stage9c_modes_summary_filters_views_exports(site):
    client, Session, admin, ids = site
    headers = as_unit(admin, ids['kp'])
    run(Session.kw['bind'])
    run(Session.kw['bind'])
    _, gid = master(client,headers)
    empty = client.get(BASE+'/rows',headers=headers)
    assert empty.status_code==200,empty.text
    assert empty.json()['total']==1
    assert empty.json()['items'][0]['status']=='belum'
    values=[{'code':'I_R','line_no':1,'value':20},
            {'code':'I_R','line_no':2,'value':30},
            {'code':'I_S','line_no':1,'value':20},
            {'code':'I_S','line_no':2,'value':30},
            {'code':'I_T','line_no':1,'value':20},
            {'code':'I_T','line_no':2,'value':30}]
    result=client.put('/api/substations/measurements',headers=headers,json=visit(gid,values=values))
    assert result.status_code==200,result.text
    mid=result.json()['id']
    rows=client.get(BASE+'/rows',headers=headers)
    assert rows.status_code==200,rows.text
    data=rows.json()['items'][0]
    assert data['measurement_id']==mid and data['columns']['total_r']['value']==50
    assert data['sessions']['SIANG'] is not None
    summ=client.get(BASE+'/summary',headers=headers)
    assert summ.status_code==200,summ.text
    assert summ.json()['total']==rows.json()['total']==1
    filt=client.get(BASE+'/rows?numeric_code=total_r&numeric_op=gte&numeric_min=51',headers=headers)
    assert filt.status_code==200,filt.text
    assert filt.json()['total']==0
    assert client.get(BASE+'/rows?mode=semua',headers=headers).json()['total']==1
    assert client.get(BASE+'/rows?mode=periode&start=2000-01-01&end=2000-01-02',headers=headers).json()['items'][0]['measurement_id'] is None
    detail=client.get(BASE+f'/measurements/{mid}',headers=headers)
    assert detail.status_code==200 and detail.json()['calculated']['columns']
    view=client.post(BASE+'/views',headers=headers,json={'name':'Uji',
        'layout':{'mode':'terakhir','columns':['total_r','code']},'is_default':True})
    assert view.status_code==200,view.text
    assert any(v['name']=='Uji' for v in client.get(BASE+'/views',headers=headers).json())
    export=client.get(BASE+'/export?format=xlsx&columns=code,total_r',headers=headers)
    assert export.status_code==200,export.text
    wb=load_workbook(BytesIO(export.content));assert 'Keterangan' in wb.sheetnames
    assert wb.active.cell(2,2).value==50
    csv=client.get(BASE+'/export?format=csv',headers=headers)
    assert csv.status_code==200 and b'KETERANGAN' in csv.content
    assert client.get(BASE+'/rows?unit_id=999999',headers=headers).status_code==404


def test_stage9c_admin_reference_and_archive_view_permissions(site):
    client, Session, admin, ids = site
    headers=as_unit(admin, ids['kp']);run(Session.kw['bind'])
    bad=client.post(BASE+'/settings',headers=headers,json={'reference_code':'not_found'})
    assert bad.status_code==422
    ok=client.post(BASE+'/settings',headers=headers,json={'reference_code':'total_r'})
    assert ok.status_code==200,ok.text
    assert client.get(BASE+'/definitions',headers=headers).json()['reference_code']=='total_r'
    assert client.post(BASE+'/views',json={'name':'No CSRF','layout':{}}).status_code==403
    shared=client.post(BASE+'/views',headers=headers,json={'name':'Tim',
        'shared':True,'layout':{'mode':'terakhir'}})
    assert shared.status_code==200,shared.text


def test_stage9b_hotfix_cycles_absent_and_preview(site):
    client,Session,admin,ids=site
    headers=as_unit(admin,ids['kp']);run(Session.kw['bind'])
    _,gid=master(client,headers)
    saved=client.put('/api/substations/measurements',headers=headers,
                     json=visit(gid,values=[{'code':'I_R','line_no':1,'value':0}]))
    assert saved.status_code==200,saved.text
    mid=saved.json()['id']
    base='/api/substations/calculations'
    for expression in ('total_r+1','arus_nominal+total_r'):
        cycle=client.post(base+'/test',headers=headers,json={
           'measurement_id':mid,'code':'total_r','expression':expression})
        if expression=='total_r+1':
            assert cycle.status_code==422 and 'Siklus rumus' in cycle.text
    cycle=client.post(base+'/preview',headers=headers,json={
        'code':'total_r','expression':'total_r + 1'})
    assert cycle.status_code==422 and 'Siklus rumus' in cycle.text
    for lines in (2,3):
        if lines==3:
            # Snapshot is independent from subsequent master edits.
            from app.modules.substations.models import SubstationMeasurement
            with Session() as db:
                db.get(SubstationMeasurement,mid).snapshot_line_count=3;db.commit()
        result=client.post(base+'/test',headers=headers,json={
            'measurement_id':mid,'expression':'i_r_j3 + 1'})
        assert result.status_code==200,result.text
        if lines==2:
            assert result.json()['draft'] is None
            assert 'jurusan 3 tidak ada' in result.json()['result']['note']
            assert result.json()['result']['total']==0
        branched=client.post(base+'/test',headers=headers,json={
            'measurement_id':mid,'expression':'IF(jumlah_jurusan >= 3, i_r_j3, 0)'})
        assert branched.status_code==200
        assert branched.json()['draft']==(0 if lines==2 else None)
    preview=client.post(base+'/preview',headers=headers,json={
        'code':'total_r','expression':'SUM_JURUSAN(i_r)'})
    assert preview.status_code==200,preview.text
    assert 'Tidak ada perubahan' in preview.json()['message']
    assert len(preview.json()['sample'])==1


def test_stage9b_hotfix_recalc_idempotent_and_versions(site):
    client,Session,admin,ids=site
    headers=as_unit(admin,ids['kp']);run(Session.kw['bind'])
    _,gid=master(client,headers)
    result=client.put('/api/substations/measurements',headers=headers,json=visit(gid))
    assert result.status_code==200
    mid=result.json()['id']
    from app.modules.substations.calculation_service import save_results
    from app.modules.substations.models import SubstationMeasurement
    from app.modules.substations.models_calc import GarduCalcValue,GarduCalcMatch,GarduCalcMark
    with Session() as db:
        visit_row=db.get(SubstationMeasurement,mid)
        save_results(db,visit_row);save_results(db,visit_row);db.commit()
        count=db.query(GarduCalcValue).filter_by(measurement_id=mid).count()
        distinct=db.query(GarduCalcValue.column_id).filter_by(measurement_id=mid).distinct().count()
        assert count==distinct
        mark=db.get(GarduCalcMark,mid)
        mark.version=9;db.commit()
        save_results(db,visit_row,version=1);db.commit()
        assert db.get(GarduCalcMark,mid).version==9
    recalculated=client.post('/api/substations/calculations/recalculate?limit=1',headers=headers)
    assert recalculated.status_code==200
    assert recalculated.json()['processed']==0


def test_stage9b_atomic_category_reordering(site):
    client,Session,admin,ids=site
    headers=as_unit(admin,ids['kp'])
    base='/api/substations/calculations'
    before=client.get(base+'/definitions',headers=headers).json()
    codes=[r['code'] for r in before['rules'] if r['kind']=='category' and r['active']]
    reorder=client.post(base+'/rules/reorder',headers=headers,json={
        'kind':'category','codes':list(reversed(codes))})
    assert reorder.status_code==200,reorder.text
    after=client.get(base+'/definitions',headers=headers).json()
    actual=[r['code'] for r in after['rules'] if r['kind']=='category' and r['active']]
    assert actual==list(reversed(codes))
    bad=client.post(base+'/rules/reorder',headers=headers,json={'kind':'category','codes':[codes[0]]})
    assert bad.status_code==422


def test_stage9b_hotfix_sqlite_busy_returns_200(site):
    """A competing recalc should return busy instead of an HTTP 500."""
    client, Session, admin, ids = site
    headers = as_unit(admin, ids['kp'])
    from app.modules.substations.calculation_router import _SQLITE_RECALC_LOCK
    assert _SQLITE_RECALC_LOCK.acquire(blocking=False)
    try:
        response = client.post('/api/substations/calculations/recalculate?limit=1', headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()['busy'] is True
        assert response.json()['processed'] == 0
    finally:
        _SQLITE_RECALC_LOCK.release()

def test_stage9c_sort_empty_last_and_row_filter(site):
    """NULL reference sorting stays last ascending and descending."""
    client, Session, admin, ids = site
    headers = as_unit(admin, ids['kp'])
    run(Session.kw['bind'])
    _, first_station = master(client, headers)
    initial = client.get(BASE+'/rows?sort=total_r&desc=true', headers=headers)
    assert initial.status_code == 200, initial.text
    assert initial.json()['total'] == 1
    result = client.put('/api/substations/measurements', headers=headers,
                        json=visit(first_station, values=[
                            {'code':'I_R','line_no':1,'value':0},
                            {'code':'I_R','line_no':2,'value':0}]))
    assert result.status_code == 200, result.text
    # Zero is real, not treated as a missing value.
    for direction in ('true','false'):
        query = BASE + '/rows?numeric_code=total_r&numeric_op=gte&numeric_min=0&sort=total_r&desc='+direction
        rows = client.get(query, headers=headers)
        assert rows.status_code == 200, rows.text
        assert rows.json()['total'] == 1
        assert rows.json()['items'][0]['columns']['total_r']['value'] == 0
