/** 9d-4: the master form only ever sends fields the API accepts (fixes "Ubah gardu" 422). */
export const TEXT = ['name', 'address', 'brand', 'tap', 'serial_number', 'ownership', 'purpose'];
export const NUMBER = ['power_kva', 'phase', 'line_count'];
export const OPTIONAL_NUMBER = ['year', 'lat', 'lon', 'feeder_id'];
const FORM_KEYS = ['unit_id', 'code', ...TEXT, ...NUMBER, ...OPTIONAL_NUMBER, 'line_labels', 'extra_values'];
export function formFromRow(blank, row) {
  const out = { ...blank };
  for (const key of FORM_KEYS) {
    const value = row[key];
    if (value === null || value === undefined || typeof value === 'object') continue;
    out[key] = String(value);
  }
  out.line_labels = (row.line_labels || []).join('|');
  out.extra_values = JSON.stringify(row.extra_values || {});
  return out;
}
export function editableBody(form, creating, withUnit) {
  const body = {};
  if (creating) body.code = (form.code || '').trim();
  for (const key of TEXT) body[key] = (form[key] ?? '').trim() || null;
  if (body.name === null) body.name = '';
  for (const key of NUMBER) body[key] = Number(form[key]);
  for (const key of OPTIONAL_NUMBER) body[key] = form[key] === '' || form[key] == null ? null : Number(String(form[key]).replace(',', '.'));
  body.line_labels = form.line_labels ? form.line_labels.split('|').map(v => v.trim()).filter(Boolean) : [];
  let extra = {};
  try { extra = form.extra_values ? JSON.parse(form.extra_values) : {}; } catch { throw new Error('Atribut tambahan tidak sah'); }
  body.extra_values = extra;
  if (withUnit && form.unit_id) body.unit_id = Number(form.unit_id);
  return body;
}
