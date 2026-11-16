"""Pure organizational rules for unit hierarchy and inherited permissions."""
import re

CODE = re.compile(r'^[a-z][a-z0-9_]*$')
ROLE_KEY = re.compile(r'^[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)*$')
LEVELS = ('up3', 'ulp', 'kp')

class OrgError(ValueError):
    pass

def validate_code(code):
    if not isinstance(code, str) or len(code) > 80 or not CODE.fullmatch(code):
        raise OrgError('Kode unit harus huruf kecil, angka atau underscore dan diawali huruf')
    return code

def validate_role_key(value):
    if value is None or value == '':
        return None
    if not isinstance(value, str) or len(value) > 60 or not ROLE_KEY.fullmatch(value):
        raise OrgError('Kunci peran tidak valid (contoh: system.load)')
    return value

def validate_creation(level, parent, units):
    if level not in LEVELS:
        raise OrgError('Tingkat unit tidak valid')
    if level == 'up3':
        if parent is not None or any(u['level'] == 'up3' for u in units):
            raise OrgError('Hanya satu UP3 tanpa induk yang diizinkan')
        return
    required = 'up3' if level == 'ulp' else 'ulp'
    if parent is None or parent['level'] != required or not parent['active']:
        raise OrgError(f'{level.upper()} wajib di bawah {required.upper()} aktif')
    children = [u for u in units if u['parent_id'] == parent['id'] and u['level'] == level]
    if len(children) >= 100:
        raise OrgError('Batas 100 unit anak per induk telah tercapai')
    if level == 'ulp' and sum(u['level'] == 'ulp' for u in units) >= 100:
        raise OrgError('Batas 100 ULP telah tercapai')

def validate_deactivation(unit, units):
    if unit['level'] == 'up3':
        raise OrgError('UP3 tidak boleh dinonaktifkan')
    if any(u['parent_id'] == unit['id'] and u['active'] for u in units):
        raise OrgError('Unit masih mempunyai anak aktif')

def ancestors(unit_id, units):
    by_id = {u['id']: u for u in units}
    result, seen = [], {unit_id}
    cursor = by_id.get(unit_id)
    while cursor and cursor['parent_id'] is not None:
        parent_id = cursor['parent_id']
        if parent_id in seen:
            raise OrgError('Siklus hierarki unit')
        seen.add(parent_id)
        cursor = by_id.get(parent_id)
        if cursor:
            result.append(parent_id)
    return result

def descendants(unit_id, units):
    result, found = [], {unit_id}
    pending = [unit_id]
    while pending:
        parent = pending.pop(0)
        for unit in units:
            if unit['parent_id'] == parent and unit['id'] not in found:
                found.add(unit['id'])
                result.append(unit['id'])
                pending.append(unit['id'])
    return result

def can_read(access, unit_id, units):
    """For future use only: access is iterable of {'unit_id','role'} records."""
    return any(unit_id == a['unit_id'] or unit_id in descendants(a['unit_id'], units)
               for a in access)

def can_write(access, unit_id, units):
    """Data roles inherit to descendants; configuration is admin-global only."""
    return any(a.get('role') in ('operator', 'verifier') and (
        a['unit_id'] == unit_id or unit_id in descendants(a['unit_id'], units))
        for a in access)
