"""Stage 6 navigation metadata stays isolated from electrical topology."""
from fastapi.testclient import TestClient
from test_stage4a_units import site, login, as_unit
from app import main
from app.modules.topology.service import EMPTY_LAYOUT


def symbol(link=None):
    result={'id':'symlink','type':'feeder','x':10,'y':10,'w':100,'h':70,
            'asset_code':None,'label':'Ke unit bawah','rotation':0}
    if link is not None:result['link']=link
    return result


def layout(link=None):
    return {**EMPTY_LAYOUT,'symbols':[symbol(link)]}


def create(client,headers,unit,link=None):
    return client.post('/api/topology',headers=as_unit(headers,unit),
                       json={'name':'Diagram QA','layout':layout(link)})


def test_links_hierarchy_and_legacy_layout(site):
    admin, _, head, ids = site
    root, ulp, kp = ids['root'], ids['other'], ids['kp']
    root_diagram=create(admin,head,root)
    ulp_diagram=create(admin,head,ulp)
    kp_diagram=create(admin,head,kp)
    assert all(r.status_code==201 for r in (root_diagram,ulp_diagram,kp_diagram))
    root_id, ulp_id, kp_id=(r.json()['id'] for r in (root_diagram,ulp_diagram,kp_diagram))
    assert root_diagram.json()['layout']['symbols'][0].get('link') is None
    valid={'unit_id':ulp,'diagram_id':ulp_id}
    updated=admin.put(f'/api/topology/{root_id}',headers=as_unit(head,root),json={
        'name':'Root linked','expected_version':1,'layout':layout(valid)})
    assert updated.status_code==200,updated.text
    assert updated.json()['layout']['symbols'][0]['link']==valid
    # all invalid directions, unit/diagram mismatch and missing diagram are rejected
    for source, target in [(ulp,{'unit_id':root,'diagram_id':root_id}),
                           (ulp,{'unit_id':ulp,'diagram_id':ulp_id}),
                           (ulp,{'unit_id':ids['home'],'diagram_id':root_id}),
                           (kp,{'unit_id':ulp,'diagram_id':ulp_id}),
                           (root,{'unit_id':ulp,'diagram_id':kp_id}),
                           (root,{'unit_id':kp,'diagram_id':999999})]:
        bad=create(admin,head,source,target)
        assert bad.status_code==422,(source,target,bad.status_code,bad.text)
    allowed=create(admin,head,ulp,{'unit_id':kp,'diagram_id':kp_id})
    assert allowed.status_code==201,allowed.text
    assert admin.get('/api/topology/browse',headers=as_unit(head,root)).status_code==200
    assert {u['unit_id'] for u in admin.get('/api/topology/link-targets',headers=as_unit(head,root)).json()} >= {ulp,kp}
    with TestClient(main.app) as viewer:
        vh=login(viewer,'operator_kp')
        view=viewer.get('/api/topology/browse',headers=as_unit(vh,kp))
        assert view.status_code==200 and {u['unit_id'] for u in view.json()}=={kp}
        assert viewer.get('/api/topology/link-targets',headers=as_unit(vh,kp)).json()==[]
        assert viewer.put(f'/api/topology/{kp_id}',headers=as_unit(vh,kp),json={
            'name':'Forbidden','expected_version':1,'layout':layout(valid)}).status_code==403


def test_revision_preserves_link_and_archived_restore_rejected(site):
    admin,_,head,ids=site
    ulp,kp=ids['other'],ids['kp']
    target=create(admin,head,kp).json()['id']
    linked={'unit_id':kp,'diagram_id':target}
    original=create(admin,head,ulp,linked)
    assert original.status_code==201,original.text
    source_id=original.json()['id']
    revisions=admin.get(f'/api/topology/{source_id}/revisions',headers=as_unit(head,ulp))
    assert revisions.json()[0]['snapshot']['layout']['symbols'][0]['link']==linked
    removed=admin.put(f'/api/topology/{source_id}',headers=as_unit(head,ulp),json={
        'name':'Removed link','expected_version':1,'layout':layout()})
    assert removed.status_code==200,removed.text
    restored=admin.post(f'/api/topology/{source_id}/restore-version',headers=as_unit(head,ulp),json={
        'version':1,'expected_version':2})
    assert restored.status_code==200,restored.text
    assert restored.json()['layout']['symbols'][0]['link']==linked
    removed=admin.put(f'/api/topology/{source_id}',headers=as_unit(head,ulp),json={
        'name':'Removed again','expected_version':3,'layout':layout()})
    assert removed.status_code==200
    archived=admin.post(f'/api/topology/{target}/archive',headers=as_unit(head,kp))
    assert archived.status_code==200
    rejected=admin.post(f'/api/topology/{source_id}/restore-version',headers=as_unit(head,ulp),json={
        'version':1,'expected_version':4})
    assert rejected.status_code==422 and 'symlink' in rejected.text
    assert admin.get('/api/topology/link-targets',headers=as_unit(head,ulp)).json()[0]['diagrams']==[]


def test_cycle_guard_rejects_invalid_existing_graph(site):
    """Defence in depth if an older imported JSON contains a forbidden back-link."""
    admin, Session, headers, ids = site
    root_id=create(admin,headers,ids['root']).json()['id']
    ulp_id=create(admin,headers,ids['other']).json()['id']
    from app.modules.topology.models import TopologyDiagram
    with Session() as db:
        row=db.get(TopologyDiagram, ulp_id)
        row.layout=layout({'unit_id':ids['root'],'diagram_id':root_id})
        db.commit()
    attempt=admin.put(f'/api/topology/{root_id}',headers=as_unit(headers,ids['root']),
                      json={'name':'Cycle refused','expected_version':1,
                            'layout':layout({'unit_id':ids['other'],'diagram_id':ulp_id})})
    assert attempt.status_code==422 and 'siklus' in attempt.text
