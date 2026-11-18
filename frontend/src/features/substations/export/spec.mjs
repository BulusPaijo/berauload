export const MAX_COLUMNS = 60;
const NUMERIC = ['unit_id', 'feeder_id', 'min_kva', 'max_kva', 'numeric_min', 'numeric_max'];
const DROP = ['page', 'page_size'];
export const emptyFilter = () => ({ mode: 'terakhir', session: 'tertinggi', sort: 'code', desc: 'false', findings: [], finding_mode: 'any' });

export function filterBody(state) {
  const out = {};
  for (const [key, value] of Object.entries(state)) {
    if (DROP.includes(key) || value === '' || value === null || value === undefined) continue;
    if (key === 'findings') { if (value.length) out.findings = [...value]; continue; }
    if (key === 'desc') { out.desc = value === true || value === 'true'; continue; }
    if (NUMERIC.includes(key)) { const n = Number(value); if (Number.isFinite(n)) out[key] = n; continue; }
    out[key] = value;
  }
  return out;
}

export function buildSpec({ columns, shape, format, delimiter }) {
  return {
    columns: columns.map(c => (c.header && c.header.trim() ? { key: c.key, header: c.header.trim() } : { key: c.key })),
    shape, format, delimiter,
  };
}

export function moveColumn(columns, index, step) {
  const to = index + step;
  if (to < 0 || to >= columns.length) return columns;
  const next = [...columns];
  [next[index], next[to]] = [next[to], next[index]];
  return next;
}

export function addColumn(columns, key) {
  if (columns.some(c => c.key === key) || columns.length >= MAX_COLUMNS) return columns;
  return [...columns, { key }];
}

export function removeColumn(columns, key) { return columns.filter(c => c.key !== key); }
export function renameColumn(columns, key, header) { return columns.map(c => (c.key === key ? { ...c, header } : c)); }

export function groupCatalog(items, chosenKeys, search, shape) {
  const q = (search || '').trim().toLowerCase();
  const taken = new Set(chosenKeys);
  const groups = new Map();
  for (const item of items) {
    if (taken.has(item.key)) continue;
    if (shape === 'long' && item.key.startsWith('param:')) continue;
    if (q && !`${item.label} ${item.key}`.toLowerCase().includes(q)) continue;
    if (!groups.has(item.group)) groups.set(item.group, []);
    groups.get(item.group).push(item);
  }
  return [...groups.entries()].map(([group, entries]) => ({ group, entries }));
}

export function validateSpec({ columns, shape }, catalogKeys) {
  const problems = [];
  if (!columns.length) problems.push('Pilih minimal satu kolom');
  if (columns.length > MAX_COLUMNS) problems.push(`Maksimal ${MAX_COLUMNS} kolom`);
  if (shape === 'long' && columns.some(c => c.key.startsWith('param:'))) problems.push('Bentuk panjang tidak memakai kolom nilai ukur lebar');
  const missing = columns.filter(c => catalogKeys && !catalogKeys.has(c.key)).map(c => c.key);
  if (missing.length) problems.push(`Kolom tidak tersedia lagi: ${missing.join(', ')}`);
  if (columns.some(c => (c.header || '').length > 80)) problems.push('Judul kolom maksimal 80 karakter');
  return problems;
}

export function fromTemplate(template, catalogKeys) {
  const spec = template.spec || {};
  const all = Array.isArray(spec.columns) ? spec.columns : [];
  const kept = all.filter(c => !catalogKeys || catalogKeys.has(c.key));
  const dropped = all.filter(c => catalogKeys && !catalogKeys.has(c.key)).map(c => c.key);
  return {
    columns: kept.map(c => ({ key: c.key, ...(c.header ? { header: c.header } : {}) })),
    shape: spec.shape === 'long' ? 'long' : 'wide',
    format: spec.format === 'csv' ? 'csv' : 'xlsx',
    delimiter: spec.delimiter === ',' ? ',' : ';',
    dropped,
  };
}

export function sizeNote(total, limit) {
  if (total > limit) return { level: 'error', text: `Terlalu banyak: ${total.toLocaleString('id-ID')} baris, batas ${limit.toLocaleString('id-ID')}. Persempit filter.` };
  if (total > limit * 0.6) return { level: 'warn', text: `${total.toLocaleString('id-ID')} baris; unduhan bisa memakan waktu beberapa puluh detik.` };
  return { level: 'ok', text: `${total.toLocaleString('id-ID')} baris` };
}
