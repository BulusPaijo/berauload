"""Admin-managed operator input layout; no changes to readings or formulas."""
from ..org_units.context import UnitContext, unit_context
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import update
from sqlalchemy.orm import Session
from ...db import AuditLog, get_db, User
from ...security import current_user, require
from . import repository as repo
from .models import InputFormTab, InputFormPlacement, InputFormRevision
from .service import form_data, validate_layout

router = APIRouter(prefix='/api/input-form', tags=['Input Form Layout'], dependencies=[Depends(unit_context('read'))])


class TabSpec(BaseModel):
    code: str = Field(min_length=2, max_length=40, pattern=r'^[A-Za-z][A-Za-z0-9_]*$')
    name: str = Field(min_length=2, max_length=100)
    active: bool = True


class PlacementSpec(BaseModel):
    metric_code: str = Field(min_length=2, max_length=90)
    tab_code: str = Field(min_length=2, max_length=40)
    visible: bool = True


class LayoutSpec(BaseModel):
    expected_version: int = Field(ge=1)
    tabs: list[TabSpec] = Field(min_length=1, max_length=30)
    placements: list[PlacementSpec] = Field(max_length=2000)


@router.get('/config')
def get_layout(user: User = Depends(current_user), db: Session = Depends(get_db),
               ctx: UnitContext = Depends(unit_context('read'))):
    if ctx.unit.level == 'up3':
        return {'version': 1, 'tabs': [], 'placements': []}
    current = repo.revision(db, ctx.id)
    return form_data(repo.tabs(db, ctx.id), repo.metrics(db, ctx.id),
                     repo.placements(db, ctx.id), current.version if current else 1)


@router.put('/config')
def put_layout(body: LayoutSpec, user: User = Depends(require('admin')),
               db: Session = Depends(get_db),
               ctx: UnitContext = Depends(unit_context('configure'))):
    if ctx.unit.level == 'up3':
        raise HTTPException(422, 'UP3 tidak memiliki form input')
    old_tabs = repo.tabs(db, ctx.id)
    known = {m.code for m in repo.metrics(db, ctx.id)}
    validate_layout(old_tabs, known, body.tabs, body.placements)
    # Optimistic lock: two concurrent editors cannot overwrite each other's layout.
    updated = db.execute(update(InputFormRevision).where(
        InputFormRevision.unit_id == ctx.id,
        InputFormRevision.version == body.expected_version,
    ).values(version=body.expected_version + 1))
    if updated.rowcount != 1:
        db.rollback()
        raise HTTPException(409, 'Pengaturan telah berubah. Muat ulang sebelum menyimpan')
    old_map = {t.code: t for t in old_tabs}
    for order, tab in enumerate(body.tabs):
        if tab.code in old_map:
            item = old_map[tab.code]
            item.name, item.active, item.display_order = tab.name, tab.active, order
        else:
            db.add(InputFormTab(code=tab.code, name=tab.name, unit_id=ctx.id,
                                active=tab.active, display_order=order))
    existing = repo.placements(db, ctx.id)
    for order, placement in enumerate(body.placements):
        if placement.metric_code in existing:
            item = existing[placement.metric_code]
            item.tab_code = placement.tab_code
            item.visible = placement.visible
            item.display_order = order
        else:
            db.add(InputFormPlacement(unit_id=ctx.id, metric_code=placement.metric_code,
                    tab_code=placement.tab_code, visible=placement.visible,
                    display_order=order))
    db.add(AuditLog(user_id=user.id, action='input_form_layout_update',
                    target='input_form', unit_id=ctx.id, detail={'unit_id':ctx.id,'version': body.expected_version + 1,
                    'tabs': len(body.tabs), 'parameters': len(body.placements)}))
    db.commit()
    return get_layout(user, db, ctx)
