/** 9d-5 pure helpers: Excel-like value table + plain-language history for one measurement. */
import { columnsFromParams, headerPlan, shortLabels, unitLabel } from '../grid.mjs';

const ck = (pid, line) => `${pid}:${line}`;
const words = s => String(s ?? '').trim().split(/\s+/).filter(Boolean);
const prefix = names => {
  const lists = names.map(words);
  let k = 0;
  while (lists.length > 1 && lists.every(l => l.length > k + 1 && l[k] === lists[0][k])) k++;
  return k ? lists[0].slice(0, k).join(' ') : names[0] ?? '';
};
const phaseOf = sub => (/^netral$/i.test(sub) ? 'N' : ((/^([RSTN])(-[RSTN0])?$/.exec(sub) || [])[1] || ''));

export const fmtValue = (value, flag, flagName = f => f) => {
  if (flag) return flagName(flag);
  if (value == null || value === '') return '';
  return new Intl.NumberFormat('id-ID', { maximumFractionDigits: 3 }).format(Number(value));
};

/** Cell lookup: {value, flag, changed, before, beforeFlag} for (param, line). */
const cellOf = (values, changed) => {
  const v = new Map(values.map(x => [ck(x.param_id, x.line_no), x]));
  const c = new Map((changed || []).map(x => [ck(x.param_id, x.line_no), x]));
  return (pid, line) => {
    const row = v.get(ck(pid, line)), old = c.get(ck(pid, line));
    return { value: row?.value ?? null, flag: row?.flag ?? null, changed: !!old,
      before: old ? old.before : null, beforeFlag: old ? old.before_flag : null };
  };
};

/**
 * Per-jurusan table: rows = Jurusan 1..n, column groups = line params split by unit
 * (Arus R S T N …). Gardu-level groups (rel F-N, rel F-F, ujung, grounding) come separately.
 */
export function visitTable(params, values, lineCount, lineLabels = [], changed = []) {
  const active = params.filter(p => p.active);
  const cell = cellOf(values, changed);
  const byCode = new Map(active.map(p => [p.code, p]));
  const lineParams = active.filter(p => p.scope === 'line').sort((a, b) => a.display_order - b.display_order);
  const groups = [];
  for (const p of lineParams) {
    const last = groups[groups.length - 1];
    if (last && last.unit === p.unit) last.params.push(p); else groups.push({ unit: p.unit, params: [p] });
  }
  const head = groups.map(g => {
    const names = g.params.map(p => p.name), subs = shortLabels(names);
    return { title: g.params.length > 1 ? prefix(names) : names[0], unit: unitLabel(g.unit),
      cols: g.params.map((p, i) => ({ id: p.id, code: p.code, sub: g.params.length > 1 ? subs[i] : '', phase: phaseOf(subs[i]) })) };
  });
  const n = Math.max(1, Math.min(5, Number(lineCount) || 1));
  const rows = Array.from({ length: n }, (_, i) => ({ line: i + 1,
    label: lineLabels[i] ? String(lineLabels[i]) : `Jurusan ${i + 1}`,
    cells: head.flatMap(h => h.cols.map(c => ({ id: c.id, ...cell(c.id, i + 1) }))) }));
  const gardu = headerPlan(columnsFromParams(active.filter(p => p.scope === 'substation'), null)).map(b => ({
    title: b.title, tone: b.tone, unit: b.unit,
    cells: b.cells.map(c => { const p = byCode.get(c.code); return { id: p.id, code: c.code, sub: c.sub || p.name, phase: c.phase, ...cell(p.id, 0) }; }) }));
  const changedCount = rows.reduce((s, r) => s + r.cells.filter(c => c.changed).length, 0)
    + gardu.reduce((s, g) => s + g.cells.filter(c => c.changed).length, 0);
  return { head, rows, gardu, changedCount };
}

/** "Jurusan 1 · Arus R 120 → 125 A" (empty is "kosong", never 0). */
export function describeChange(c, flagName = f => f, lineLabels = []) {
  const where = c.line_no ? `${lineLabels[c.line_no - 1] || 'Jurusan ' + c.line_no} · ` : '';
  const show = (v, f) => (f ? flagName(f) : v == null ? 'kosong' : fmtValue(v, null));
  const unit = c.after == null && !c.after_flag ? '' : c.after_flag ? '' : ` ${unitLabel(c.unit)}`;
  return `${where}${c.name} ${show(c.before, c.before_flag)} → ${show(c.after, c.after_flag)}${unit}`.trim();
}

export const KIND_TONE = { create: 'new', save: 'edit', verify: 'ok', reopen: 'warn', update: 'edit', delete: 'danger' };

export function historyView(entries, flagName = f => f, lineLabels = []) {
  return entries.map(e => ({
    id: e.id, at: e.at, user: e.user, tone: KIND_TONE[e.kind] || 'edit', summary: e.summary,
    revision: e.revision_after ?? e.revision_before ?? null, reason: e.reason || '',
    lines: [...(e.meta || []).map(m => `${m.label}: ${m.before ?? 'kosong'} → ${m.after ?? 'kosong'}`),
            ...(e.kind === 'create' ? [] : (e.changes || []).map(c => describeChange(c, flagName, lineLabels)))],
    count: (e.changes || []).length }));
}

export const stateLabel = s => (s === 'verified' ? 'Terverifikasi' : 'Draft');
export const whenLabel = iso => {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return new Intl.DateTimeFormat('id-ID', { timeZone: 'Asia/Makassar', day: '2-digit', month: 'short',
    year: 'numeric', hour: '2-digit', minute: '2-digit' }).format(d) + ' WITA';
};
