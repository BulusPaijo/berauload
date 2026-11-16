export function initialGrant(unit, role) {
  return {unit_id: unit.id, role: unit.level === 'up3' ? 'management' : role};
}

export function validateAccess(role, grants) {
  return role !== 'admin' && !grants.length
    ? 'Pilih minimal satu unit pada bagian Akses unit sebelum membuat pengguna.'
    : '';
}

export function summarizeUserAccess(user, grants, names) {
  if (user.role === 'admin') return 'Semua unit (admin global)';
  const access = grants.filter(grant => grant.user_id === user.id);
  return access.length
    ? access.map(grant => `${names.get(grant.unit_id) ?? `Unit #${grant.unit_id}`}: ${grant.role}`).join(' · ')
    : 'Belum ada akses unit';
}
