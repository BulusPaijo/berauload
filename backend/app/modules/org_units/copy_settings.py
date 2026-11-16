"""Atomic admin-only copy of *configuration* without operational data."""
import re
from fastapi import HTTPException
from sqlalchemy.orm import Session
from ...db import Asset, Metric, AuditLog
from ..formulas.models import FormulaDefinition
from ..input_forms.models import InputFormTab, InputFormPlacement, InputFormRevision
from ..input_forms.migrations import DEFAULT_TABS
from ..topology.models import TopologyDiagram, TopologyRevision
from .models import OrgUnit


def mapped_code(code: str, source: str, destination: str, max_len: int) -> str:
    old_prefix = source + '_'
    tail = code[len(old_prefix):] if code.startswith(old_prefix) else code
    generated = destination + '_' + tail
    if len(generated) > max_len or not re.fullmatch('[a-z][a-z0-9_]*', generated):
        raise HTTPException(422, f'Kode salinan melampaui batas atau tidak valid: {generated}')
    return generated


def _plan(db: Session, source: OrgUnit, destination: OrgUnit, include_topology: bool):
    if source.id == destination.id or not source.active or not destination.active:
        raise HTTPException(422, 'Unit sumber dan tujuan harus berbeda serta aktif')
    if destination.level == 'up3':
        raise HTTPException(422, 'UP3 bukan tujuan salin konfigurasi input')
    assets = db.query(Asset).filter_by(unit_id=source.id).order_by(Asset.id).all()
    metrics = db.query(Metric).filter_by(unit_id=source.id).order_by(Metric.id).all()
    selected = [m for m in metrics if m.input_mode == 'input']
    formulas = {f.metric_id: f for f in db.query(FormulaDefinition).filter_by(unit_id=source.id)}
    computed = [m for m in metrics if m.input_mode == 'computed' and m.id in formulas]
    all_metrics = selected + computed
    tabs = db.query(InputFormTab).filter_by(unit_id=source.id).order_by(InputFormTab.id).all()
    placements = db.query(InputFormPlacement).filter_by(unit_id=source.id).all()
    diagrams = db.query(TopologyDiagram).filter_by(unit_id=source.id, archived=False).all() if include_topology else []
    if (db.query(Asset.id).filter_by(unit_id=destination.id).first() or
        db.query(Metric.id).filter_by(unit_id=destination.id).first() or
        db.query(FormulaDefinition.id).filter_by(unit_id=destination.id).first() or
        db.query(InputFormPlacement.id).filter_by(unit_id=destination.id).first() or
        db.query(TopologyDiagram.id).filter_by(unit_id=destination.id).first()):
        raise HTTPException(409, 'Unit tujuan tidak kosong')
    amap = {a.code: mapped_code(a.code, source.code, destination.code, 80) for a in assets}
    mmap = {m.code: mapped_code(m.code, source.code, destination.code, 90) for m in all_metrics}
    combined = [*amap.values(), *mmap.values()]
    if len(set(amap.values())) != len(amap) or len(set(mmap.values())) != len(mmap):
        raise HTTPException(409, 'Kode salinan bentrok satu sama lain')
    if db.query(Asset.id).filter(Asset.code.in_(amap.values())).first() or db.query(Metric.id).filter(
            Metric.code.in_(mmap.values())).first():
        raise HTTPException(409, 'Kode hasil pemetaan sudah dipakai secara global')
    tabmap = {t.code: f'u{destination.id}_{t.code.split("_",1)[1]}'
              if t.code.startswith(f'u{source.id}_') else
              f'u{destination.id}_{t.code}' for t in tabs}
    if any(len(x) > 40 for x in tabmap.values()):
        raise HTTPException(422, 'Kode tab hasil salin melebihi 40 karakter')
    if diagrams:
        for diagram in diagrams:
            for box in diagram.layout.get('boxes', []):
                if box.get('rule_id') is not None:
                    raise HTTPException(422, 'Diagram menggunakan Engineering Rule yang tidak disalin')
                if box.get('asset_code') and box['asset_code'] not in amap:
                    raise HTTPException(422, 'Diagram merujuk peralatan di luar konfigurasi salinan')
                if any(code not in mmap for code in box.get('metric_codes', [])):
                    raise HTTPException(422, 'Diagram merujuk parameter di luar konfigurasi salinan')
    return assets, all_metrics, formulas, tabs, placements, diagrams, amap, mmap, tabmap


def preview(db: Session, source: OrgUnit, destination: OrgUnit, include_topology: bool):
    result = _plan(db, source, destination, include_topology)
    assets, metrics, formulas, tabs, placements, diagrams, amap, mmap, tabmap = result
    return {'source_unit_id': source.id, 'destination_unit_id': destination.id,
            'assets': amap, 'metrics': mmap, 'tabs': tabmap,
            'counts': {'assets': len(assets), 'input_metrics': sum(m.input_mode=='input' for m in metrics),
                       'formulas': len(formulas), 'tabs': len(tabs),
                       'placements': len(placements), 'diagrams': len(diagrams)},
            'will_copy_readings': False, 'will_copy_day_states': False}


def _expression(expression: str, mapping: dict) -> str:
    from ..formulas.engine import parse_formula
    _parsed, refs = parse_formula(expression)
    unknown = set(refs) - mapping.keys()
    if unknown:
        raise HTTPException(422, 'Formula memiliki referensi di luar unit yang disalin: '+ ', '.join(sorted(unknown)))
    return re.sub(r'\b[a-z][a-z0-9_]*\b', lambda match: mapping.get(match.group(), match.group()), expression)


def _copy_assets(db, assets, destination_id, amap):
    id_map = {}
    for a in assets:
        row = Asset(code=amap[a.code], name=a.name, kind=a.kind,
                    active=a.active, unit_id=destination_id)
        db.add(row);db.flush()
        id_map[a.id] = row.id
    return id_map


def _copy_metrics(db, metrics, formulas, destination_id, mmap, asset_ids):
    for m in metrics:
        row = Metric(code=mmap[m.code], name=m.name, unit=m.unit,
                     group_name=m.group_name, input_mode=m.input_mode,
                     display_order=m.display_order, active=m.active,
                     asset_id=asset_ids.get(m.asset_id), role_key=m.role_key,
                     unit_id=destination_id)
        db.add(row);db.flush()
        if m.id in formulas:
            db.add(FormulaDefinition(metric_id=row.id, unit_id=destination_id,
                                     expression=_expression(formulas[m.id].expression, mmap),
                                     version=1, created_by=formulas[m.id].created_by))


def _copy_tabs(db, tabs, placements, destination_id, tabmap, mmap):
    existing = {row.code: row for row in db.query(InputFormTab).filter_by(unit_id=destination_id)}
    for t in tabs:
        code = tabmap[t.code]
        row = existing.get(code)
        if row is None:
            row = InputFormTab(code=code, unit_id=destination_id)
            db.add(row)
        row.name, row.active, row.display_order = t.name, t.active, t.display_order
    for p in placements:
        if p.metric_code in mmap:
            db.add(InputFormPlacement(unit_id=destination_id, metric_code=mmap[p.metric_code],
                                      tab_code=tabmap[p.tab_code], visible=p.visible,
                                      display_order=p.display_order))
    revision = db.query(InputFormRevision).filter_by(unit_id=destination_id).first()
    if revision:
        revision.version += 1


def _copy_diagrams(db, diagrams, destination_id, amap, mmap, actor_id):
    from copy import deepcopy
    for diagram in diagrams:
        layout = deepcopy(diagram.layout)
        for symbol in layout.get('symbols', []):
            if symbol.get('asset_code'):
                if symbol['asset_code'] not in amap:
                    raise HTTPException(422, 'Diagram merujuk peralatan di luar salinan')
                symbol['asset_code'] = amap[symbol['asset_code']]
        for box in layout.get('boxes', []):
            if box.get('asset_code'):
                box['asset_code'] = amap[box['asset_code']]
            box['metric_codes'] = [mmap[code] for code in box.get('metric_codes', [])]
        row = TopologyDiagram(name=diagram.name, description=diagram.description,
                              layout=layout, unit_id=destination_id, updated_by=actor_id)
        db.add(row);db.flush()
        db.add(TopologyRevision(diagram_id=row.id, version=1,
                                snapshot={'name':row.name,'description':row.description,
                                          'layout':layout}, updated_by=actor_id))


def commit(db: Session, source: OrgUnit, destination: OrgUnit,
           include_topology: bool, actor_id: int):
    items = _plan(db, source, destination, include_topology)
    assets, metrics, formulas, tabs, placements, diagrams, amap, mmap, tabmap = items
    try:
        asset_ids = _copy_assets(db, assets, destination.id, amap)
        _copy_metrics(db, metrics, formulas, destination.id, mmap, asset_ids)
        _copy_tabs(db, tabs, placements, destination.id, tabmap, mmap)
        _copy_diagrams(db, diagrams, destination.id, amap, mmap, actor_id)
        totals = {'assets':len(assets), 'metrics':len(metrics),
                  'formulas':len(formulas), 'tabs':len(tabs),
                  'placements':len(placements), 'diagrams':len(diagrams)}
        db.add(AuditLog(unit_id=destination.id, user_id=actor_id,
            action='org_settings_copy', target=f'unit:{destination.id}',
            detail={'source_unit_id':source.id,'destination_unit_id':destination.id,
                    'actor_role':'admin_global','counts':totals}))
        db.commit()
        return {'ok':True,'counts':totals,'source_unit_id':source.id,
                'destination_unit_id':destination.id}
    except Exception:
        db.rollback()
        raise
