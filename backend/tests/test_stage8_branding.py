"""Stage 8 integration on synthetic SQLite; no production credentials/data."""
from io import BytesIO
from pathlib import Path
import os
from PIL import Image, PngImagePlugin
from sqlalchemy import select, func, create_engine
from fastapi.testclient import TestClient
from app.modules.branding.defaults import DEFAULTS
from app.modules.branding.models import AppBranding
from app.modules.branding.migrations import run, VERSION
from app.modules.branding.service import image_path, sheet_title, slug
from app.modules.formulas.models import SchemaMigration
from app.db import AuditLog
from test_stage4a_units import site, login


def png(width=36,height=36,metadata=False):
    stream=BytesIO()
    info=PngImagePlugin.PngInfo() if metadata else None
    if info: info.add_text('Comment', 'sensitive metadata')
    Image.new('RGB',(width,height),'navy').save(stream,format='PNG',pnginfo=info)
    return stream.getvalue()


def test_public_defaults_and_migration_idempotent(site):
    client, Session, headers, ids=site
    r=client.get('/api/branding')
    assert r.status_code==200
    assert all(r.json()[key]==value for key,value in DEFAULTS.items())
    assert 'password' not in r.text and 'user_id' not in r.text
    assert r.headers['etag'] and r.headers['cache-control']
    assert client.get('/api/branding', headers={'If-None-Match':r.headers['etag']}).status_code==304
    for icon in ('logo','favicon'):
        response=client.get('/api/branding/'+icon)
        assert response.status_code==200 and b'<svg' in response.content
        assert response.headers['x-content-type-options']=='nosniff'
    eng=Session.kw['bind']
    with Session() as db:
        assert db.query(AppBranding).count()==0
        assert db.query(SchemaMigration).filter_by(version=VERSION).count()==1
    run(eng);run(eng)
    with Session() as db:
        assert db.query(AppBranding).count()==0
        assert db.query(SchemaMigration).filter_by(version=VERSION).count()==1


def test_edit_access_validation_audit(site):
    client, Session, headers, ids=site
    payload={'app_name':'  Energi Test  ','app_short_name':'Test',
             'color_primary':'#123456','color_accent':'#AABBCC'}
    with TestClient(client.app) as unauth:
        assert unauth.put('/api/branding',json=payload).status_code==401
        assert unauth.post('/api/branding/logo',files={'file':('a.png',png())}).status_code==401
        assert unauth.delete('/api/branding/logo').status_code==401
    assert client.put('/api/branding',headers={'X-CSRF-Token':'invalid'},json=payload).status_code==403
    with TestClient(client.app) as operator:
        oh=login(operator,'operator_u')
        assert operator.put('/api/branding',headers=oh,json=payload).status_code==403
    response=client.put('/api/branding',headers=headers,json=payload)
    assert response.status_code==200,response.text
    assert response.json()['app_name']=='Energi Test'
    assert response.json()['color_primary']=='#123456'
    with Session() as db:
        assert db.query(AuditLog).filter_by(action='branding_update').count()==1
        assert db.get(AppBranding,1).updated_by is not None
    for value in ('#FFFFFF','no-color','#fff'):
        assert client.put('/api/branding',headers=headers,json={'color_primary':value}).status_code==422
    for value in ('  ','a'*41,'xyz\x01'):
        assert client.put('/api/branding',headers=headers,json={'app_name':value}).status_code==422
    assert client.put('/api/branding',headers=headers,json={'unknown':'key'}).status_code==422


def test_upload_reencode_safety_and_reset(site,monkeypatch,tmp_path):
    client, Session, headers, ids=site
    monkeypatch.setenv('UPLOAD_DIR',str(tmp_path/'uploads'))
    def upload(kind, content, filename='evil.png'):
        return client.post('/api/branding/'+kind,headers=headers,
                           files={'file':(filename,content,'image/png')})
    assert upload('logo',png(metadata=True),'../../x.png').status_code==200
    stored=image_path('logo')
    assert stored==tmp_path/'uploads'/'branding'/'logo.png'
    assert stored.exists()
    assert b'sensitive metadata' not in stored.read_bytes()
    assert client.get('/api/branding/logo?v=1').headers['content-type'].startswith('image/png')
    for content in (b'<svg><script>alert(1)</script></svg>', b'PK\x03\x04zip',
                    b'<?php echo 1 ?>', b'<html>payload</html>', b'GIF89a', b'BMxxx'):
        assert upload('logo',content).status_code==422
    assert upload('logo',png(1025,1)).status_code==422
    assert upload('logo',png() + b'\0'*(512*1024)).status_code==422
    ico=BytesIO();Image.new('RGBA',(32,32),'blue').save(ico,format='ICO')
    assert upload('favicon',ico.getvalue(),'../favicon.ico').status_code==200
    assert image_path('favicon').read_bytes().startswith(b'\x89PNG')
    assert client.delete('/api/branding/favicon',headers=headers).status_code==200
    assert not image_path('favicon').exists()
    assert client.post('/api/branding/reset',headers=headers).status_code==200
    assert not stored.exists()
    assert client.get('/api/branding').json()['app_name']=='BerauLoad'


def test_branding_report_compatibility_and_sheet_names(site):
    client, Session, headers, ids=site
    assert sheet_title('Invalid [a]/'*6).count('[')==0
    assert len(sheet_title('a'*70))<=31
    assert slug('=x/abc')=='x_abc'
    legacy=client.get('/api/reports/export?start=2026-11-01&end=2026-11-03',headers=headers)
    assert legacy.status_code==200,legacy.text
    from openpyxl import load_workbook
    assert load_workbook(BytesIO(legacy.content)).sheetnames[0]=='Pembacaan Per Jam'
    assert client.put('/api/branding',headers=headers,json={'app_name':'Energi Test',
         'app_short_name':'Rekap/UP3', 'organization_name':'Organisasi Test'}).status_code==200
    report=client.get('/api/reports/export?start=2026-11-01&end=2026-11-03',headers=headers)
    assert report.status_code==200,report.text
    assert load_workbook(BytesIO(report.content)).sheetnames[0]=='Data Rekap_UP3'
    pdf=client.get('/api/reports/pdf?start=2026-11-01&end=2026-11-03',headers=headers)
    assert pdf.status_code==200 and pdf.content.startswith(b'%PDF')
    # Schema marker remains independent from display name.
    from app.modules.template_import.workbook import build
    assert 'berauload_hourly' in Path('backend/app/modules/template_import/workbook.py').read_text()
