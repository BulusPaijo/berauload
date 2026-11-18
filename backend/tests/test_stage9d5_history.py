"""Stage 9d-5: readable measurement detail, history in plain language, per-measurement Excel."""
import io
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from app import main
from test_stage4a_units import site, login, as_unit
from test_stage9a_substations import visit
from test_stage9d4_kp import gardu

S = '/api/substations'


def test_detail_header_history_and_changed_cells(site):
    client, Session, admin, units = site
    with TestClient(main.app) as v:
        vh = as_unit(login(v, 'verifier_u'), units['other'])
        gid = v.post(S + '/master', headers=vh, json=gardu('GH01')).json()['id']
        first = v.put(S + '/measurements', headers=vh, json=visit(gid, values=[
            {'code': 'I_R', 'line_no': 1, 'value': 120}, {'code': 'I_S', 'line_no': 1, 'value': 98},
            {'code': 'V_R0', 'line_no': 0, 'value': 231}]))
        assert first.status_code == 200, first.text
        mid, rev = first.json()['id'], first.json()['revision']
        second = v.put(S + '/measurements', headers=vh, json=visit(gid, rev, values=[
            {'code': 'I_R', 'line_no': 1, 'value': 125}, {'code': 'I_S', 'line_no': 1, 'value': 98},
            {'code': 'V_R0', 'line_no': 0, 'value': None}]))
        assert second.status_code == 200 and second.json()['revision'] == rev + 1
        d = v.get(f'{S}/measurements/{mid}', headers=vh).json()
        assert d['header']['substation_code'] == 'GH01' and d['header']['substation_name'] == 'Gardu GH01'
        assert d['header']['unit_name'] and d['header']['session_name']
        newest, oldest = d['history'][0], d['history'][-1]
        assert oldest['kind'] == 'create' and 'membuat pengukuran dengan 3 nilai' in oldest['summary']
        assert newest['kind'] == 'save' and 'mengubah 2 nilai' in newest['summary']
        assert newest['revision_before'] == rev and newest['revision_after'] == rev + 1
        changes = {(c['code'], c['line_no']): (c['before'], c['after']) for c in newest['changes']}
        assert changes == {('I_R', 1): (120, 125), ('V_R0', 0): (231, None)}   # cleared cell -> None, not 0
        cells = {(c['line_no'], c['before']) for c in d['changed_cells']}
        assert cells == {(1, 120), (0, 231)}
        ver = v.post(S + '/measurements/actions', headers=vh, json={'ids': [mid], 'action': 'verify'})
        assert ver.status_code == 200
        d = v.get(f'{S}/measurements/{mid}', headers=vh).json()
        assert d['history'][0]['kind'] == 'verify' and 'memverifikasi' in d['history'][0]['summary']
        assert len(d['changed_cells']) == 2                   # verify does not hide the last value edit
        assert d['header']['verified_by_name']
        listed = v.get(S + '/measurements', headers=vh, params={'substation_id': gid}).json()['items'][0]
        assert listed['substation_code'] == 'GH01' and listed['substation_name'] == 'Gardu GH01'


def test_single_measurement_excel_marks_changed_cells(site):
    client, Session, admin, units = site
    with TestClient(main.app) as v, TestClient(main.app) as k:
        vh = as_unit(login(v, 'verifier_u'), units['other'])
        gid = v.post(S + '/master', headers=vh, json=gardu('GH02')).json()['id']
        made = v.put(S + '/measurements', headers=vh, json=visit(gid, values=[
            {'code': 'I_R', 'line_no': 2, 'value': 40}])).json()
        v.put(S + '/measurements', headers=vh, json=visit(gid, made['revision'], values=[
            {'code': 'I_R', 'line_no': 2, 'value': 44}]))
        res = v.get(f"{S}/measurements/{made['id']}/xlsx", headers=vh)
        assert res.status_code == 200 and 'pengukuran_GH02_2034-01-02_SIANG.xlsx' in res.headers['content-disposition']
        ws = load_workbook(io.BytesIO(res.content)).active
        cells = {(c.row, c.column): c for row in ws.iter_rows() for c in row}
        hit = [c for c in cells.values() if c.value == 44]
        assert hit and hit[0].comment and 'Sebelumnya: 40' in hit[0].comment.text
        assert hit[0].fill.fgColor.rgb.endswith('FCD9B6')
        blank = [c for c in cells.values() if c.value == 0]
        assert not blank                                     # empty cells stay empty, never 0
        kh = as_unit(login(k, 'operator_kp'), units['kp'])
        assert k.get(f"{S}/measurements/{made['id']}/xlsx", headers=kh).status_code == 404
