"""V1.4.6 report source/presentation regression using test-only SQLite records."""
import io
import os
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook

root = Path(tempfile.mkdtemp(prefix='berauload_report_'))
os.environ.setdefault('DATABASE_URL', 'sqlite:///' + str(root / 'report.db'))
os.environ.setdefault('UPLOAD_DIR', str(root / 'uploads'))
os.environ.setdefault('ADMIN_PASSWORD', 'Report-Test-Admin-Password-2026')

from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal, Metric, HourRecord, Reading
from app.modules.report_builder.migrations import run as migrate, VERSION
from app.modules.formulas.models import SchemaMigration
from app.db import engine

CAP = 'daya_pasok_pembangkit_kw'
LOAD = 'beban_sistem_kw'


def login(client, name='admin', password=None):
    result = client.post('/api/auth/login', json={'username': name, 'password': password or os.environ['ADMIN_PASSWORD']})
    assert result.status_code == 200, result.text
    return {'X-CSRF-Token': result.json()['csrf']}


def block(kind='stat', code=LOAD):
    return {'id': 'block_report_1', 'kind': kind, 'title': 'Beban Sistem', 'text': '',
            'metric_codes': [code], 'aggregation': 'avg', 'granularity': 'day'}


def make_template(client, headers, **kwargs):
    spec = {'name': 'Laporan Beban V146', 'scope': 'personal', 'description': '', 'blocks': [block()]}
    spec.update(kwargs)
    resp = client.post('/api/report-builder', headers=headers, json=spec)
    assert resp.status_code == 201, resp.text
    return resp.json()


def seed_data(day=date(2027, 3, 14)):
    with SessionLocal() as db:
        if db.query(HourRecord.id).filter_by(day=day, hour=0).first():
            return
        ids = {m.code: m.id for m in db.query(Metric).filter(Metric.code.in_([CAP, LOAD]))}
        for hour, cap, load in ((0, 50000, 0), (1, 52000, None), (2, 51000, 48000)):
            record = HourRecord(day=day, hour=hour,
                                timestamp_utc=datetime(2027, 3, 13, 16+hour, tzinfo=timezone.utc))
            db.add(record)
            db.flush()
            for code, value in ((CAP, cap), (LOAD, load)):
                if value is not None:
                    db.add(Reading(hour_id=record.id, metric_id=ids[code],
                                   value=Decimal(value), source='test'))
        db.commit()


def test_report_crud_preview_pdf_xlsx():
    with TestClient(app) as client:
        h = login(client)
        seed_data()
        blocks = [
            {'id':'intro_v146', 'kind':'text', 'title':'Catatan Manajemen',
             'text':'=HYPERLINK("x")', 'metric_codes':[], 'granularity':'day','aggregation':'avg'},
            block(),
            {'id':'pairs_v146', 'kind':'chart', 'title':'Daya Mampu vs Beban',
             'text':'', 'metric_codes':[CAP, LOAD], 'aggregation':'avg','granularity':'hour'},
        ]
        item = make_template(client, h, blocks=blocks)
        ident = item['id']
        response = client.post('/api/report-builder/preview', headers=h, json={
            'blocks': blocks, 'start':'2027-03-14', 'end':'2027-03-14'})
        assert response.status_code == 200, response.text
        result = response.json()['blocks']
        assert result[1]['value'] == 24000  # zero is valid; missing is excluded
        rows = result[2]['rows']
        assert len(rows) == 24  # Explicit 24 slots, no interpolation through missing hours.
        assert rows[0][LOAD] == 0 and rows[1][LOAD] is None
        assert rows[2][LOAD] == 48000 and rows[3][LOAD] is None
        url = f'/api/report-builder/{ident}/download?start=2027-03-14&end=2027-03-14'
        pdf = client.get(url+'&format=pdf')
        assert pdf.status_code == 200 and pdf.content.startswith(b'%PDF')
        xlsx = client.get(url+'&format=xlsx')
        assert xlsx.status_code == 200 and xlsx.content.startswith(b'PK')
        sheet = load_workbook(io.BytesIO(xlsx.content), read_only=True, data_only=False).active
        assert any(isinstance(row[0], str) and row[0].startswith("'=HYPERLINK")
                   for row in sheet.values if row and row[0])
        assert client.get(url+'&format=csv').status_code == 422


def test_report_version_conflict_duplicate_archive():
    with TestClient(app) as client:
        h = login(client)
        created = make_template(client, h)
        id = created['id']
        edit = {k:created[k] for k in ('name','description','scope','blocks')}
        edit.update(name='Laporan Beban Revisi', expected_version=1)
        new = client.put(f'/api/report-builder/{id}', headers=h, json=edit)
        assert new.status_code == 200 and new.json()['version'] == 2
        assert client.put(f'/api/report-builder/{id}', headers=h, json=edit).status_code == 409
        duplicate = client.post(f'/api/report-builder/{id}/duplicate', headers=h)
        assert duplicate.status_code == 201
        assert duplicate.json()['scope'] == 'personal'
        assert client.post(f'/api/report-builder/{id}/archive', headers=h).status_code == 200
        assert client.get(f'/api/report-builder/{id}/download?start=2027-03-14&end=2027-03-14').status_code == 404
        assert all(t['id'] != id for t in client.get('/api/report-builder').json())


def test_report_auth_and_validation():
    with TestClient(app) as admin:
        h = login(admin)
        admin.post('/api/users', headers=h, json={'username':'reportviewer146',
            'display_name':'Laporan Viewer', 'role':'management', 'accesses': _qa_grants('management'),
            'password':'Viewer-Report-Strong-2026'})
        shared = make_template(admin, h, scope='system')
        personal = make_template(admin, h)
        with TestClient(app) as viewer:
            from app.modules.org_units.repository import home_unit
            with SessionLocal() as db:
                home={'X-Unit-Id':str(home_unit(db).id)}
            uh = login(viewer, 'reportviewer146', 'Viewer-Report-Strong-2026')
            assert viewer.get('/api/report-builder').json() == []
            visible = viewer.get('/api/report-builder',headers=home).json()
            assert shared['id'] in [x['id'] for x in visible]
            assert personal['id'] not in [x['id'] for x in visible]
            assert viewer.post('/api/report-builder', headers={**uh,**home}, json={
                'name':'Tidak Boleh', 'scope':'system','blocks':[block()]}).status_code == 403
            assert viewer.put(f'/api/report-builder/{shared["id"]}', headers={**uh,**home}, json={
                'name':'Edit Tak Berhak', 'scope':'system','blocks':[block()],
                'expected_version':1}).status_code == 403
            assert viewer.get(f'/api/report-builder/{personal["id"]}/download?start=2027-03-14&end=2027-03-14',headers=home).status_code == 404
        bad = block('chart')
        bad['metric_codes'] = [CAP, 'feeder_1_r_a']
        assert admin.post('/api/report-builder/preview', headers=h, json={
            'blocks':[bad], 'start':'2027-03-14','end':'2027-03-14'}).status_code == 422
        assert admin.post('/api/report-builder/preview', headers=h, json={
            'blocks':[block()], 'start':'2027-03-14','end':'2028-12-31'}).status_code == 422


def test_style_whitelist_and_legacy_defaults():
    with TestClient(app) as client:
        h = login(client)
        panel = {'id':'styling-v146','title':'Beban Puncak', 'kind':'stat','source':'metric',
                 'metric_codes':[LOAD], 'style_preset':'dark','font_family':'mono',
                 'title_font_size':18,'value_font_size':40,
                 'text_color':'#F4F4F4','background_color':'#122b38','border_color':'#225769'}
        created = client.post('/api/dashboard-builder', headers=h, json={
            'name':'Dashboard Styling', 'panels':[panel]})
        assert created.status_code == 201, created.text
        assert created.json()['panels'][0]['style_preset'] == 'dark'
        for field, value in [('text_color','red;position:absolute'),('font_family','unsafe'),
                             ('value_font_size',100),('style_preset','unrecognized')]:
            test_panel = {**panel, field:value}
            result = client.post('/api/dashboard-builder', headers=h, json={
                'name':'Invalid Panel', 'panels':[test_panel]})
            assert result.status_code == 422
        old = client.post('/api/dashboard-builder', headers=h, json={
            'name':'Legacy Layout', 'panels':[{k:v for k,v in panel.items()
             if k not in {'style_preset','font_family','title_font_size','value_font_size','text_color','background_color','border_color'}}]})
        assert old.status_code == 201
        assert old.json()['panels'][0]['style_preset'] == 'classic'


def test_migration_is_repeatable():
    migrate(engine)
    migrate(engine)
    with SessionLocal() as db:
        assert db.query(SchemaMigration).filter_by(version=VERSION).count() == 1


def _qa_grants(role):
    """Updated synthetic fixture: Stage 4c requires explicit unit grants."""
    from app.modules.org_units.repository import home_unit, root
    with SessionLocal() as db:
        unit = root(db) if role == 'management' else home_unit(db)
        return [{'unit_id': unit.id, 'role': role}]
