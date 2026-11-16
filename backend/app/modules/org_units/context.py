"""Unit scope and effective data roles for V1.6.0 Stage 4a.

No client-supplied unit is trusted without a database membership check.
Configuration authorization remains global-admin-only.
"""
from dataclasses import dataclass
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ...db import User, get_db
from ...security import current_user
from .models import OrgUnit, UserUnitAccess
from .repository import home_unit


@dataclass(frozen=True)
class UnitContext:
    unit: OrgUnit
    actor: User
    roles: frozenset[str]
    superadmin: bool

    @property
    def id(self) -> int:
        return self.unit.id

    def role_for(self, action: str) -> str:
        if self.superadmin:
            return 'admin_global'
        if action not in self.roles:
            raise HTTPException(403, f'Tidak memiliki hak {action} pada unit ini')
        return action


def _accessible_rows(db: Session, user: User):
    return (db.query(UserUnitAccess, OrgUnit)
            .join(OrgUnit, OrgUnit.id == UserUnitAccess.unit_id)
            .filter(UserUnitAccess.user_id == user.id, OrgUnit.active.is_(True))
            .all())


def _default_unit(db: Session, actor: User, rows):
    if actor.role == 'admin':
        return home_unit(db)
    if not rows:
        raise HTTPException(403, 'Pengguna belum mempunyai akses unit aktif')
    rank = {'up3': 0, 'ulp': 1, 'kp': 2}
    return min((unit for _, unit in rows),
               key=lambda u: (rank[u.level], u.display_order, u.id))


def _effective_roles(db: Session, unit: OrgUnit, rows):
    lineage = {unit.id}
    cursor = unit
    while cursor.parent_id is not None:
        cursor = db.get(OrgUnit, cursor.parent_id)
        if cursor is None or not cursor.active:
            raise HTTPException(404, 'Hierarki unit tidak aktif')
        lineage.add(cursor.id)
    return frozenset(access.role for access, _ in rows if access.unit_id in lineage)


def unit_context(mode: str = 'read'):
    if mode not in ('read', 'write_data', 'configure'):
        raise ValueError('Mode unit tidak dikenal')

    def resolve(request: Request, db: Session = Depends(get_db),
                actor: User = Depends(current_user)) -> UnitContext:
        rows = _accessible_rows(db, actor)
        requested = request.headers.get('X-Unit-Id')
        if requested is None:
            unit = _default_unit(db, actor, rows)
        else:
            if not requested.isascii() or not requested.isdecimal() or len(requested) > 12:
                raise HTTPException(422, 'X-Unit-Id harus angka ID unit')
            unit = db.get(OrgUnit, int(requested))
        if unit is None or not unit.active:
            raise HTTPException(404, 'Unit tidak ditemukan atau nonaktif')
        privileged = actor.role == 'admin'
        roles = _effective_roles(db, unit, rows) if not privileged else frozenset()
        if not privileged and not roles:
            raise HTTPException(404, 'Unit tidak ditemukan')
        if mode == 'configure' and not privileged:
            raise HTTPException(403, 'Hanya admin global boleh mengatur konfigurasi')
        if mode == 'write_data':
            if not privileged and not roles.intersection(('operator', 'verifier')):
                raise HTTPException(403, 'Unit hanya dapat dibaca')
            if unit.level == 'up3':
                raise HTTPException(422, 'Pilih ULP atau KP untuk mengisi data')
        return UnitContext(unit, actor, roles, privileged)

    return resolve


def require_action(context: UnitContext, action: str) -> str:
    """Verifier may finalize; operator inputs; global admin can do both."""
    if action not in ('operator', 'verifier'):
        raise ValueError('Aksi tidak dikenal')
    return context.role_for(action)


def audit_details(context: UnitContext, action: str, **details):
    return {'unit_id': context.id, 'actor_role': require_action(context, action), **details}


def require_metric(db: Session, code: str, unit_id: int):
    from ...db import Metric
    row = db.query(Metric).filter_by(code=code, unit_id=unit_id).first()
    if row is None:
        raise HTTPException(404, 'Parameter tidak ditemukan')
    return row
