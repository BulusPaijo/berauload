"""Isolation-only smoke: always uses its own fresh SQLite DB, never production."""
import os, tempfile
from pathlib import Path
root=Path(tempfile.mkdtemp(prefix='berauload_pytest_'))
os.environ['DATABASE_URL']='sqlite:///'+str(root/'test.db')
os.environ['UPLOAD_DIR']=str(root/'uploads')
os.environ['ADMIN_PASSWORD']='Test-Strong-Password-123456'
from fastapi.testclient import TestClient
from app.main import app


def test_auth_input_lock_reports_and_import():
    with TestClient(app) as c:
        assert c.get('/api/health').status_code==200
        auth=c.post('/api/auth/login',json={'username':'admin','password':os.environ['ADMIN_PASSWORD']})
        assert auth.status_code==200
        headers={'X-CSRF-Token':auth.json()['csrf']}
        assert c.put('/api/records/2026-11-01/0',json={'values':{'pltd_kw':100}}).status_code==403
        values={'pltu_lati_cb33_kw':2938,'pltu_lati_cb31_kw':4602,
           'sewa_tama_1_kw':5000,'sewa_tama_2_kw':5000,'pltd_kw':2400,
           'pltu_berau_og3_kw':4924,'pltu_berau_og4_kw':1366,
           'pltd_berau_kw':725,'beban_suaran_kw':1714.18,'incoming_gi_kw':7870}
        result=c.put('/api/records/2026-11-01/0',json={'values':values},headers=headers)
        assert result.status_code==200
        assert result.json()['computed']['beban_sistem_kw']==35814.18
        assert c.get('/api/dashboard?year=2026&month=11').json()['peak_kw']==35814.18
        # An unrelated measurement correction must not erase the cached recap.
        assert c.put('/api/records/2026-11-01/0',json={'values':{'frequency_hz':50}},headers=headers).status_code==200
        d=c.get('/api/records/day?day=2026-11-01').json()
        assert d['hours'][0]['values']['beban_sistem_kw']==35814.18
        assert c.post('/api/days/2026-11-01/verify',json={'reason':'Sudah diuji'},headers=headers).status_code==200
        assert c.post('/api/days/2026-11-01/finalize',json={'reason':'Hasil final'},headers=headers).status_code==200
        assert c.put('/api/records/2026-11-01/0',json={'values':{'pltd_kw':500}},headers=headers).status_code==409
        pdf=c.get('/api/reports/pdf?start=2026-11-01&end=2026-11-01')
        assert pdf.status_code==200 and pdf.content.startswith(b'%PDF-')
        xlsx=c.get('/api/reports/export?start=2026-11-01&end=2026-11-01')
        assert xlsx.status_code==200 and xlsx.content.startswith(b'PK')
        assert c.post('/api/assets',json={'code':'test_asset','name':'Test Asset','kind':'pembangkit'},headers=headers).status_code==200
        result=c.post('/api/metrics',json={'code':'test_measure_kw','name':'Test Measure','unit':'kW','group_name':'PEMBANGKIT'},headers=headers)
        assert result.status_code==200
        assert c.put('/api/records/2026-11-02/0',json={'values':{'test_measure_kw':123.5}},headers=headers).status_code==200
        assert c.post('/api/auth/logout',headers=headers).status_code==200
