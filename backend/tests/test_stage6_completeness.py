"""Read-only Stage 6 completeness, synthetic SQLite and fixed WITA clock."""
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import event
from test_stage4a_units import site, login, as_unit
from app import main
from app.db import Metric, User
from app.modules.completeness import service, export
from app.modules.org_units.models import OrgUnit, UnitDayState

TODAY = '2026-11-16'


def test_counts_zero_basis_and_future(site, monkeypatch):
    admin, Session, headers, ids = site
    monkeypatch.setattr(service, 'clock_now', lambda: datetime(2026, 11, 16, 10, 1,
                                                             tzinfo=ZoneInfo('Asia/Makassar')))
    for hour, values in [(0, {'kp_load': 0}), (4, {'kp_load': 9}),
                         (15, {'kp_load': 22})]:
        result = admin.put(f'/api/records/{TODAY}/{hour}',
                           headers=as_unit(headers, ids['kp']), json={'values': values})
        assert result.status_code == 200, result.text
    url=f'/api/org-units/{ids["other"]}/completeness?start={TODAY}&end=2026-11-17'
    data=admin.get(url, headers=as_unit(headers, ids['other']))
    assert data.status_code == 200, data.text
    kp=next(row for row in data.json()['rows'] if row['unit_id']==ids['kp'])
    assert kp['basis']=='any_input'
    assert kp['days'][0]['filled_hours']==2  # 15:00 is not started
    assert kp['days'][0]['expected_hours']==11  # current 10:00 WITA started
    assert kp['days'][1]['future'] and kp['days'][1]['expected_hours']==0
    with Session() as db:
        db.query(Metric).filter_by(code='kp_load').update({'role_key':'system.load'})
        db.commit()
    data=admin.get(url,headers=as_unit(headers,ids['other']))
    kp=next(r for r in data.json()['rows'] if r['unit_id']==ids['kp'])
    assert kp['basis']=='system.load' and kp['days'][0]['filled_hours']==2
    with Session() as db:
        db.query(Metric).filter_by(code='kp_load').update({'active':False})
        db.commit()
    inactive=admin.get(url,headers=as_unit(headers,ids['other']))
    kp_inactive=next(r for r in inactive.json()['rows'] if r['unit_id']==ids['kp'])
    assert kp_inactive['basis']=='system.load' and kp_inactive['days'][0]['filled_hours']==2
    assert kp['summary']['percent']==round(200/11,2)
    assert data.json()['summary']['expected_hours']==22
    assert admin.get(f'/api/org-units/{ids["kp"]}/completeness?start=2026-10-01&end=2026-12-03',
                     headers=as_unit(headers,ids['kp'])).status_code==422
    assert admin.get(f'/api/org-units/{ids["kp"]}/completeness?start=2026-11-17&end=2026-11-16',
                     headers=as_unit(headers,ids['kp'])).status_code==422
    assert admin.get(f'/api/org-units/{ids["kp"]}/completeness?start=bad&end=2026-11-16',
                     headers=as_unit(headers,ids['kp'])).status_code==422


def test_permissions_status_and_inactive(site, monkeypatch):
    admin, Session, head, ids=site
    monkeypatch.setattr(service,'clock_now',lambda:datetime(2026,11,17,0,0,tzinfo=ZoneInfo('Asia/Makassar')))
    with Session() as db:
        db.add(UnitDayState(unit_id=ids['kp'],day=datetime(2026,11,16).date(),status='final'))
        db.commit()
    path=f'/api/org-units/{ids["other"]}/completeness?start={TODAY}&end={TODAY}'
    with TestClient(main.app) as kp:
        kh=login(kp,'operator_kp')
        mine=kp.get(path.replace(str(ids['other']),str(ids['kp'])), headers=as_unit(kh,ids['kp']))
        assert mine.status_code==200 and len(mine.json()['rows'])==1
        assert kp.get(path,headers=as_unit(kh,ids['kp'])).status_code==404
    with TestClient(main.app) as ulp:
        uh=login(ulp,'operator_u')
        seen=ulp.get(path,headers=as_unit(uh,ids['other']))
        assert {r['unit_id'] for r in seen.json()['rows']}=={ids['other'],ids['kp']}
        assert next(r for r in seen.json()['rows'] if r['unit_id']==ids['kp'])['summary']['final_days']==1
        assert ulp.get(path.replace(str(ids['other']),str(ids['home'])),headers=as_unit(uh,ids['other'])).status_code==404
    with TestClient(main.app) as root:
        rh=login(root,'management_root')
        result=root.get(path.replace(str(ids['other']),str(ids['root'])),headers=as_unit(rh,ids['root']))
        assert result.status_code==200
        assert ids['root'] not in {r['unit_id'] for r in result.json()['rows']}
        assert ids['home'] in {r['unit_id'] for r in result.json()['rows']}
    with Session() as db:
        db.query(OrgUnit).filter_by(id=ids['kp']).update({'active':False});db.commit()
    result=admin.get(path,headers=as_unit(head,ids['other']))
    assert ids['kp'] not in {r['unit_id'] for r in result.json()['rows']}


def test_query_count_and_xlsx_cleanup(site,monkeypatch):
    admin, Session, head, ids=site
    original=export.tempfile.mkstemp
    created=[]
    def record_temp(*args,**kwargs):
        fd,path=original(*args,**kwargs);created.append(path);return fd,path
    monkeypatch.setattr(export.tempfile,'mkstemp',record_temp)
    with Session() as db:
        for label, prefix in [('kp','='),('other','+'),('home','-'),('foreign_kp','@')]:
            db.query(OrgUnit).filter_by(id=ids[label]).update({'name':prefix+'BADFORMULA'})
        db.commit()
    url=f'/api/org-units/{ids["root"]}/completeness?start=2026-09-16&end={TODAY}'
    with Session() as db:
        engine=db.get_bind();sql=[]
        def count(_conn,_cursor,statement,*args):
            if 'readings' in statement and 'GROUP BY' in statement.upper():sql.append(statement)
        event.listen(engine,'before_cursor_execute',count)
        try:
            result=service.build(db,service.allowed_units(db,db.query(User).filter_by(username='admin').one(),ids['root']),
                                 datetime(2026,9,16).date(),datetime(2026,11,16).date(),
                                 datetime(2026,11,17,tzinfo=ZoneInfo('Asia/Makassar')))
        finally:event.remove(engine,'before_cursor_execute',count)
        assert len(sql)==1 and len(result['dates'])==62
    resp=admin.get(url.replace('/completeness?','/completeness/export?'),headers=as_unit(head,ids['root']))
    assert resp.status_code==200,resp.text
    workbook=load_workbook(BytesIO(resp.content),read_only=True)
    assert workbook.sheetnames==['Kelengkapan Harian','Ringkasan dan Dasar']
    values=[row[0] for row in workbook.worksheets[0].values if row[0]]
    assert all(any(str(value).startswith("'") and symbol+"BADFORMULA" in str(value) for value in values)
               for symbol in "=+-@")
    workbook.close()
    assert created and all(not Path(p).exists() for p in created)
