"""Compare user baselines and report a non-partial conflict per hour."""
from decimal import Decimal
from fastapi import HTTPException
from ...db import AuditLog, User


def equal_value(a, b):
    if a is None or b is None:
        return a is None and b is None
    return Decimal(str(a)) == Decimal(str(b))


def last_editor(db, code: str, day, hour, unit_id: int):
    target = f'{day} {hour:02d}:00'
    rows = db.query(AuditLog).filter_by(action='hour_save', target=target).order_by(
        AuditLog.id.desc()).limit(100).all()
    for row in rows:
        detail = row.detail or {}
        if detail.get('unit_id') != unit_id or code not in detail.get('changes', {}):
            continue
        actor = db.get(User, row.user_id)
        return (actor.display_name if actor else None,
                row.created_at.isoformat() if row.created_at else None)
    return None, None


def check_base(db, values, base, previous, day, hour, unit_id):
    """Only attempted actual changes conflict; unchanged payloads are no-ops."""
    if base is None:
        return
    conflicts = []
    for code, mine in values.items():
        server = previous.get(code)
        if equal_value(server, mine):
            continue
        if code not in base:
            raise HTTPException(422, f'Nilai dasar tidak tersedia: {code}')
        if not equal_value(server, base[code]):
            who, when = last_editor(db, code, day, hour, unit_id)
            conflicts.append({'kode': code, 'nilai_anda': mine,
                              'nilai_server': server, 'diubah_oleh': who,
                              'waktu': when})
    if conflicts:
        raise HTTPException(409, {'message': 'Data berubah sejak dimuat',
                                  'conflicts': conflicts})
