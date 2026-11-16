"""V1.4.4: real API, isolated SQLite, CSV/XLSX and dashboard management tests."""
import csv
import io
import os
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from openpyxl import load_workbook

root = Path(tempfile.mkdtemp(prefix='berauload_v144_'))
os.environ['DATABASE_URL'] = 'sqlite:///' + str(root / 'test.db')
os.environ['UPLOAD_DIR'] = str(root / 'uploads')
os.environ['ADMIN_PASSWORD'] = 'V144-Secure-Admin-Passphrase-2026'

from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal, Metric, Reading, HourRecord, engine
from app.modules.dashboard_builder.migrations import run_management, MANAGEMENT_VERSION
from app.modules.data_export.migrations import run as run_export, VERSION as EXPORT_VERSION
from app.modules.formulas.models import SchemaMigration

CAP = 'daya_pasok_pembangkit_kw'
LOAD = 'beban_sistem_kw'


def login(client, name='admin', pwd=None):
    r = client.post('/api/auth/login', json={'username': name, 'password': pwd or os.environ['ADMIN_PASSWORD']})
    assert r.status_code == 200, r.text
    return {'X-CSRF-Token': r.json()['csrf']}


def seed():
    with SessionLocal() as db:
        codes = {m.code: m.id for m in db.query(Metric).filter(Metric.code.in_([CAP, LOAD])).all()}
        day = date(2026, 11, 5)
        for hour, cap, load in [(0, 50000, 0), (1, 52000, None), (2, 51000, 48000)]:
            record = HourRecord(day=day, hour=hour, timestamp_utc=datetime(2026, 11, 4, 16+hour, tzinfo=timezone.utc))
            db.add(record); db.flush()
            for code, value in [(CAP, cap), (LOAD, load)]:
                if value is not None:
                    db.add(Reading(hour_id=record.id, metric_id=codes[code], value=Decimal(value), source='test'))
        db.commit()


def payload(**diff):
    data = {'start': '2026-11-05', 'end': '2026-11-05', 'granularity': 'hour',
            'aggregation': 'avg', 'columns': ['tanggal','jam',CAP,LOAD],
            'headers': {}, 'unit_overrides': {}, 'format': 'csv'}
    data.update(diff)
    return data


def test_custom_export_csv_order_null_zero_and_xlsx():
    with TestClient(app) as client:
        h=login(client);seed()
        spec=payload(columns=['jam', LOAD, 'tanggal', CAP])
        r=client.post('/api/data-export/preview',headers=h,json=spec)
        assert r.status_code==200,r.text
        rows=r.json()['rows']
        assert rows[0]==['00:00',0,'2026-11-05',50000]
        assert rows[1][1] is None and rows[1][3]==52000
        result=client.post('/api/data-export/download',headers=h,json=spec)
        assert result.status_code==200,result.text
        parsed=list(csv.reader(io.StringIO(result.content.decode('utf-8-sig')),delimiter=';'))
        assert parsed[1][0]=='00:00' and parsed[1][1]=='0.0'
        assert parsed[2][1]=='' and parsed[2][3]=='52000.0'
        xlsx=client.post('/api/data-export/download',headers=h,json=payload(format='xlsx'))
        assert xlsx.status_code==200,xlsx.text
        wb=load_workbook(io.BytesIO(xlsx.content),read_only=True,data_only=True)
        ws=wb.active
        assert ws['D2'].value==0
        assert ws['D3'].value is None
        assert ws['C2'].value==50000


def test_aggregate_units_and_formula_injection_protection():
    with TestClient(app) as client:
        h=login(client)
        daily=payload(granularity='day',columns=['tanggal',CAP,LOAD],aggregation='avg',unit_overrides={CAP:'MW'})
        r=client.post('/api/data-export/preview',headers=h,json=daily)
        assert r.status_code==200,r.text
        assert abs(r.json()['rows'][0][1]-51)<1e-5
        assert r.json()['rows'][0][2]==24000
        assert client.post('/api/data-export/preview',headers=h,json=payload(
            unit_overrides={CAP:'kVA'})).status_code==422
        bad=payload(headers={CAP:' =HYPERLINK("test")'})
        csv_response=client.post('/api/data-export/download',headers=h,json=bad)
        parsed=list(csv.reader(io.StringIO(csv_response.content.decode('utf-8-sig')),delimiter=';'))
        assert parsed[0][2].startswith("'")
        wrong=payload(granularity='month',columns=['tanggal','jam',CAP])
        assert client.post('/api/data-export/preview',headers=h,json=wrong).status_code==422


def test_export_templates_visibility_and_protection():
    with TestClient(app) as admin:
        h=login(admin)
        spec=payload();spec.pop('start');spec.pop('end')
        item=admin.post('/api/data-export/templates',headers=h,json={
            'name':'Laporan Operasi', 'scope':'system','spec':spec})
        assert item.status_code==201,item.text
        assert admin.get('/api/data-export/templates').json()[0]['name']=='Laporan Operasi'
        admin.post('/api/users',headers=h,json={'username':'viewer144','display_name':'Viewer Export',
                        'password':'Viewer-Export-Password-2026','role':'management', 'accesses': _qa_grants('management')})
        with TestClient(app) as user:
            from app.modules.org_units.repository import home_unit
            with SessionLocal() as db:
                home={'X-Unit-Id':str(home_unit(db).id)}
            uh=login(user,'viewer144','Viewer-Export-Password-2026')
            assert user.get('/api/data-export/templates').json()==[]
            assert len(user.get('/api/data-export/templates',headers=home).json())==1
            assert user.post('/api/data-export/templates',headers={**uh,**home},json={
                'name':'Tidak Sah', 'scope':'system','spec':spec}).status_code==403
            assert user.post('/api/data-export/templates',headers={**uh,**home},json={
                'name':'Pribadi Viewer','scope':'personal','spec':spec}).status_code==403
            assert admin.get('/api/data-export/templates').json()[0]['name']=='Laporan Operasi'
            assert user.post(f"/api/data-export/templates/{item.json()['id']}/archive",headers={**uh,**home}).status_code==403


def test_dashboard_revisions_share_import_template_restore():
    with TestClient(app) as client:
        h=login(client)
        sample={'name':'Contoh Revisi','panels':[{'id':'test-one','title':'Beban',
            'kind':'line','source':'metric','metric_codes':[LOAD]}]}
        item=client.post('/api/dashboard-builder',headers=h,json=sample)
        assert item.status_code==201,item.text
        ident=item.json()['id']
        config=client.get(f'/api/dashboard-builder/{ident}/export-config')
        assert config.status_code==200 and config.json()['panels'][0]['id']=='test-one'
        imported=client.post('/api/dashboard-builder/import-config',headers=h,json=config.json())
        assert imported.status_code==201,imported.text
        assert imported.json()['scope']=='personal'
        updated=client.put(f'/api/dashboard-builder/{ident}',headers=h,json={
            'name':'Setelah Ubah','panels':sample['panels'],'expected_version':1})
        assert updated.status_code==200,updated.text
        rev=client.get(f'/api/dashboard-builder/{ident}/revisions').json()
        assert [r['version'] for r in rev]==[2,1]
        restored=client.post(f'/api/dashboard-builder/{ident}/restore-version',headers=h,
            json={'revision_id':rev[1]['id'],'expected_version':2})
        assert restored.status_code==200,restored.text
        assert restored.json()['version']==3 and restored.json()['name']=='Contoh Revisi'
        assert client.post(f'/api/dashboard-builder/{ident}/restore-version',headers=h,
            json={'revision_id':rev[1]['id'],'expected_version':2}).status_code==409
        templ=client.post('/api/dashboard-builder/manage/templates/operasi/create',headers=h)
        assert templ.status_code==201,templ.text
        client.post('/api/users',headers=h,json={'username':'shared144','display_name':'Shared Viewer',
            'password':'Shared-Dashboard-Password-2026','role':'management', 'accesses': _qa_grants('management')})
        add=client.post(f'/api/dashboard-builder/{ident}/shares',headers=h,json={'username':'shared144'})
        assert add.status_code==200,add.text
        with TestClient(app) as other:
            from app.modules.org_units.repository import home_unit
            with SessionLocal() as db:
                home={'X-Unit-Id':str(home_unit(db).id)}
            oh=login(other,'shared144','Shared-Dashboard-Password-2026')
            assert not other.get('/api/dashboard-builder').json()['items']
            assert any(x['id']==ident for x in other.get('/api/dashboard-builder',headers=home).json()['items'])
            assert other.get(f'/api/dashboard-builder/{ident}',headers=home).status_code==200
            assert other.put(f'/api/dashboard-builder/{ident}',headers={**oh,**home},json={
                'name':'Tidak Bisa','panels':[],'expected_version':3}).status_code==403
            assert other.get(f'/api/dashboard-builder/{ident}/shares',headers=home).status_code==403
        client.delete(f'/api/dashboard-builder/{ident}/shares/shared144',headers=h)
        with TestClient(app) as other:
            login(other,'shared144','Shared-Dashboard-Password-2026')
            assert other.get(f'/api/dashboard-builder/{ident}',headers=home).status_code==404


def test_migration_idempotent():
    run_export(engine);run_export(engine);run_management(engine);run_management(engine)
    with SessionLocal() as db:
        assert db.query(SchemaMigration).filter_by(version=EXPORT_VERSION).count()==1
        assert db.query(SchemaMigration).filter_by(version=MANAGEMENT_VERSION).count()==1


def test_update_template_with_version_and_archive():
    with TestClient(app) as client:
        h=login(client)
        spec=payload();spec.pop('start');spec.pop('end')
        created=client.post('/api/data-export/templates',headers=h,json={
            'name':'Template Pengujian', 'scope':'personal', 'spec':spec})
        assert created.status_code==201,created.text
        ident=created.json()['id']
        spec['columns']=['tanggal','jam',LOAD,CAP]
        update={'name':'Template Revisi','scope':'personal','spec':spec,'expected_version':1}
        changed=client.put(f'/api/data-export/templates/{ident}',headers=h,json=update)
        assert changed.status_code==200,changed.text
        assert changed.json()['version']==2 and changed.json()['spec']['columns']==spec['columns']
        assert client.put(f'/api/data-export/templates/{ident}',headers=h,json=update).status_code==409
        archived=client.post(f'/api/data-export/templates/{ident}/archive',headers=h)
        assert archived.status_code==200
        assert ident not in [r['id'] for r in client.get('/api/data-export/templates').json()]


def _qa_grants(role):
    """Updated synthetic fixture: Stage 4c requires explicit unit grants."""
    from app.modules.org_units.repository import home_unit, root
    with SessionLocal() as db:
        unit = root(db) if role == 'management' else home_unit(db)
        return [{'unit_id': unit.id, 'role': role}]
