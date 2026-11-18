/** Pure helpers for the gardu detail panel (9d-3). */
export const phaseTone = pct => pct == null ? 'none' : pct > 100 ? 'over' : pct >= 80 ? 'high' : 'ok';
export function phaseBars(byCode, codes = ['total_r', 'total_s', 'total_t', 'total_n'], nominalCode = 'arus_nominal') {
  const nominal = byCode[nominalCode]?.value ?? null;
  return codes.filter(c => byCode[c]).map((code, i) => {
    const value = byCode[code].value;
    const pct = nominal && value != null ? (value / nominal) * 100 : null;
    return { code, letter: 'RSTN'[i] ?? '', value, pct, tone: i === 3 ? 'neutral' : phaseTone(pct) };
  });
}
/** Rows of the per-jurusan table: one per line, columns = line params of one unit (A). */
export function lineTable(params, values, unit = 'A') {
  const line = params.filter(p => p.active && p.scope === 'line' && p.unit === unit).sort((a, b) => a.display_order - b.display_order);
  const words = line.map(p => p.name.split(/\s+/));
  let k = 0;
  while (line.length > 1 && words.every(w => w.length > k + 1 && w[k] === words[0][k])) k++;
  const head = words.map(w => w.slice(k).join(' '));
  const byId = new Map(line.map((p, i) => [p.id, i]));
  const lines = new Map();
  for (const v of values) {
    if (!v.line_no || !byId.has(v.param_id)) continue;
    if (!lines.has(v.line_no)) lines.set(v.line_no, Array(line.length).fill(null));
    lines.get(v.line_no)[byId.get(v.param_id)] = v.flag ?? v.value;
  }
  return { head, rows: [...lines.entries()].sort((a, b) => a[0] - b[0]).map(([n, cells]) => ({ line: n, cells })) };
}
export function trendRows(trend) {
  const days = new Map();
  for (const t of trend) { if (!days.has(t.day)) days.set(t.day, { day: t.day }); days.get(t.day)[t.session] = t.value; }
  return { sessions: [...new Set(trend.map(t => t.session))], rows: [...days.values()] };
}
export const mapsLink = (lat, lon) => (lat == null || lon == null ? null : `https://www.google.com/maps?q=${Number(lat)},${Number(lon)}`);
export const followTone = s => ({ terbuka: 'open', dikerjakan: 'work', selesai: 'done', batal: 'muted' }[s] ?? 'muted');
