"""Readable measurement header + audit history (9d-5).

Turns raw `substation_visit_*` audit rows into plain-language entries:
who did what, at which revision, and which cell changed from what to what.
"""
from ...db import AuditLog, User
from ..org_units.models import OrgUnit
from .common import dump, json_value
from .models import (Substation, SubstationFeeder, SubstationMeasurement,
                     SubstationParam, SubstationSession)

ACTION_LABEL = {
    'verify': 'memverifikasi pengukuran',
    'reopen': 'membuka kunci verifikasi',
    'update': 'mengubah data induk pengukuran',
    'delete': 'menghapus pengukuran',
}
META_LABEL = {'measured_on': 'Tanggal', 'session': 'Sesi', 'technician': 'Petugas',
              'measured_at': 'Jam ukur', 'note': 'Catatan', 'state': 'Status'}


def _num(value):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value
    return int(number) if number.is_integer() else round(number, 6)


def _cells(snapshot):
    """{(param_id, line_no): (value, flag)} from a detail() dump."""
    if not snapshot:
        return {}
    return {(v['param_id'], v['line_no']): (_num(v.get('value')), v.get('flag'))
            for v in snapshot.get('values') or []}


def value_changes(before, after, params):
    old, new = _cells(before), _cells(after)
    out = []
    for key in sorted(set(old) | set(new), key=lambda k: (k[1] or 9, params.get(k[0], {}).get('order', 0))):
        if old.get(key, (None, None)) == new.get(key, (None, None)):
            continue
        pid, line = key
        p = params.get(pid, {'code': f'#{pid}', 'name': f'Parameter #{pid}', 'unit': '', 'order': 0})
        ov, of = old.get(key, (None, None))
        nv, nf = new.get(key, (None, None))
        out.append({'param_id': pid, 'code': p['code'], 'name': p['name'], 'unit': p['unit'],
                    'line_no': line, 'before': ov, 'before_flag': of,
                    'after': nv, 'after_flag': nf})
    return out


def meta_changes(before, after):
    if not before or not after:
        return []
    return [{'field': k, 'label': label, 'before': before.get(k), 'after': after.get(k)}
            for k, label in META_LABEL.items() if before.get(k) != after.get(k)]


def _summary(kind, name, changes, meta):
    if kind == 'create':
        return f'{name} membuat pengukuran dengan {len(changes)} nilai'
    if kind == 'save':
        parts = []
        if changes:
            parts.append(f'{len(changes)} nilai')
        if meta:
            parts.append(', '.join(m['label'].lower() for m in meta))
        return f'{name} mengubah ' + (' dan '.join(parts) if parts else 'pengukuran')
    return f'{name} {ACTION_LABEL.get(kind, kind)}'


def history(db, measurement_id, limit=100):
    events = db.query(AuditLog).filter(AuditLog.target == str(measurement_id),
                                       AuditLog.action.like('substation_visit_%')
                                       ).order_by(AuditLog.id.desc()).limit(limit).all()
    params = {p.id: {'code': p.code, 'name': p.name, 'unit': p.unit, 'order': p.display_order}
              for p in db.query(SubstationParam)}
    user_ids = {e.user_id for e in events if e.user_id}
    names = {u.id: u.display_name for u in db.query(User).filter(User.id.in_(user_ids or [-1]))}
    entries = []
    for e in events:
        d = e.detail or {}
        before, after = d.get('before'), d.get('after')
        kind = e.action.removeprefix('substation_visit_')
        if kind == 'save' and before is None:
            kind = 'create'
        name = names.get(e.user_id, 'Sistem')
        changes = value_changes(before, after, params) if kind in ('save', 'create') else []
        meta = meta_changes(before, after) if kind in ('save', 'update') else []
        entries.append({
            'id': e.id, 'at': json_value(e.created_at), 'user': name, 'kind': kind,
            'actor_role': d.get('actor_role'), 'reason': d.get('reason'),
            'revision_before': (before or {}).get('revision'),
            'revision_after': (after or {}).get('revision'),
            'summary': _summary(kind, name, changes, meta),
            'changes': changes, 'meta': meta})
    return entries


def latest_changed_cells(entries):
    """Cells changed by the most recent value edit: [{param_id,line_no,before,before_flag}]."""
    for entry in entries:  # newest first
        if entry['kind'] == 'save' and entry['changes']:
            return [{k: c[k] for k in ('param_id', 'line_no', 'before', 'before_flag')}
                    for c in entry['changes']]
        if entry['kind'] == 'create':
            return []
    return []


def header(db, visit):
    gardu = db.get(Substation, visit.substation_id)
    unit = db.get(OrgUnit, visit.unit_id)
    feeder = db.get(SubstationFeeder, visit.snapshot_feeder_id) if visit.snapshot_feeder_id else None
    session = db.query(SubstationSession).filter_by(code=visit.session).first()
    users = {u.id: u.display_name for u in db.query(User).filter(User.id.in_(
        [x for x in (visit.created_by, visit.updated_by, visit.verified_by) if x] or [-1]))}
    return {'substation_code': gardu.code if gardu else None,
            'substation_name': gardu.name if gardu else None,
            'line_labels': (gardu.line_labels if gardu else None) or [],
            'unit_code': unit.code if unit else None, 'unit_name': unit.name if unit else None,
            'unit_level': unit.level if unit else None,
            'feeder_code': feeder.code if feeder else None,
            'feeder_name': feeder.name if feeder else None,
            'session_name': session.name if session else visit.session,
            'created_by_name': users.get(visit.created_by),
            'updated_by_name': users.get(visit.updated_by),
            'verified_by_name': users.get(visit.verified_by)}


def list_labels(db, rows):
    """Gardu code/name + unit code per list row in two queries (no N+1)."""
    gids = {r.substation_id for r in rows}
    uids = {r.unit_id for r in rows}
    gardu = {g.id: g for g in db.query(Substation).filter(Substation.id.in_(gids or [-1]))}
    units = {u.id: u for u in db.query(OrgUnit).filter(OrgUnit.id.in_(uids or [-1]))}
    out = []
    for r in rows:
        g, u = gardu.get(r.substation_id), units.get(r.unit_id)
        out.append({**dump(r), 'substation_code': g.code if g else None,
                    'substation_name': g.name if g else None,
                    'unit_code': u.code if u else None, 'unit_name': u.name if u else None})
    return out
