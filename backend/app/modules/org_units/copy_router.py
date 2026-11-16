"""Preview/commit of unit configuration: admin global, CSRF via standard security."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ...db import get_db, User
from ...security import require
from .models import OrgUnit
from .copy_settings import preview, commit

router = APIRouter(prefix='/api/org-units', tags=['Struktur Organisasi'])


class CopyRequest(BaseModel):
    source_unit_id: int
    include_topology: bool = False


def _units(db, source_id, dest_id):
    source, destination = db.get(OrgUnit, source_id), db.get(OrgUnit, dest_id)
    if source is None or destination is None:
        raise HTTPException(404, 'Unit sumber atau tujuan tidak ditemukan')
    return source, destination


@router.post('/{id}/copy-settings/preview')
def copy_preview(id: int, body: CopyRequest, u: User = Depends(require('admin')),
                 db: Session = Depends(get_db)):
    source, destination = _units(db, body.source_unit_id, id)
    return preview(db, source, destination, body.include_topology)


@router.post('/{id}/copy-settings/commit')
def copy_commit(id: int, body: CopyRequest, u: User = Depends(require('admin')),
                db: Session = Depends(get_db)):
    source, destination = _units(db, body.source_unit_id, id)
    return commit(db, source, destination, body.include_topology, u.id)
