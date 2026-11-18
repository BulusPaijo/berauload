/** Pure spreadsheet operations, no React or browser dependencies. */
export const visitBackupKey = (userId, unitId, day, session) =>
  `berauload:substations:v1:user:${userId}:unit:${unitId}:day:${day}:session:${session}`;
export const cellKey = (id, code, line) => `${id}|${code}|${line}`;
export const parseNumber = raw => {
  const text = String(raw ?? '').trim();
  if (!text) return null;
  const normalized = text.includes(',') && text.includes('.')
    ? text.replace(/\./g, '').replace(',', '.') : text.replace(',', '.');
  const number = Number(normalized);
  if (!Number.isFinite(number) || number < 0) throw new Error('Nilai harus angka nonnegatif');
  return number;
};
export const parsePaste = (text, startRow, startCol, rows, cols, allowed) => {
  const changes = {}, omitted = [];
  const lines = text.replace(/\r/g,'').split('\n');
  if (!lines.at(-1)) lines.pop();
  lines.forEach((line,dy)=>line.split('\t').forEach((value,dx)=>{
    const row = rows[startRow+dy], column = cols[startCol+dx];
    if (!row || !column || !allowed(row,column)) {omitted.push([dy,dx]);return;}
    changes[cellKey(row.id,column.code,column.line)] = value.trim();
  }));
  return {changes, omitted: omitted.length};
};
export const nextCell = (row, col, key, rowCount, colCount) => {
  const move = {ArrowUp:[-1,0],ArrowDown:[1,0],ArrowLeft:[0,-1],
                ArrowRight:[0,1],Enter:[1,0],Tab:[0,1]}[key];
  if (!move) return null;
  return [Math.max(0,Math.min(rowCount-1,row+move[0])),
          Math.max(0,Math.min(colCount-1,col+move[1]))];
};
export const fillDown = (rows, column, first, last, getRaw, allowed) => {
  const changes = {}, source = getRaw(rows[first],column);
  for(let i=first+1;i<=last&&i<rows.length;i++) if(allowed(rows[i],column))
    changes[cellKey(rows[i].id,column.code,column.line)] = source;
  return changes;
};
export const allowedCell = (row,column) =>
  column.line===0 || column.line<=row.line_count;
export const columnsFromParams = (params, groups=null) =>
  [...params].filter(p=>p.active && (!groups || groups.includes(p.code))).sort(
    (a,b)=>a.display_order-b.display_order).flatMap(param=>
      param.scope==='line' ? [1,2,3,4,5].map(line=>({code:param.code,
        line,label:`${param.name} J${line}`,lineLabel:line,unit:param.unit,name:param.name}))
      : [{code:param.code,line:0,label:param.name,unit:param.unit,name:param.name}]);

/** 9d-2: jurusan-first order, only up to the widest gardu on the page. */
export const orderColumns = (cols, maxLine) => {
  const top = Math.max(1, Math.min(5, maxLine || 1));
  const out = [];
  for (let n = 1; n <= top; n++) out.push(...cols.filter(c => c.line === n));
  return out.concat(cols.filter(c => c.line === 0));
};
const words = s => String(s ?? '').trim().split(/\s+/).filter(Boolean);
export const shortLabels = names => {
  const lists = names.map(words);
  if (lists.length < 2) return names.map(n => String(n));
  let k = 0;
  while (lists.every(l => l.length > k + 1 && l[k] === lists[0][k])) k++;
  return k ? lists.map(l => l.slice(k).join(' ')) : names.map(n => String(n));
};
/** Two-tier header (merged block over sub-columns), derived only from param definitions. */
const prefixWords = names => {
  const lists = names.map(words);
  let k = 0;
  while (lists.length && lists.every(l => l.length > k + 1 && l[k] === lists[0][k])) k++;
  return lists[0] ? lists[0].slice(0, k).join(' ') : '';
};
/** Gardu-level params split by subject (e.g. Tegangan rel vs Tegangan ujung) even with the same unit. */
const twoWords = col => words(col.name ?? col.label).slice(0, 2).join(' ').toLowerCase();
/** Split a gardu-level unit group by subject only when every subject has 2+ params
 *  (Tegangan rel R/S/T vs Tegangan ujung R/S/T); Grounding trafo + arester stay one block. */
/** 9d-5: gardu-level colour groups — rel fasa-netral, rel fasa-fasa, ujung JTR, grounding. */
export const TONE_TITLE = { relfn: 'Tegangan Rel F-N', relff: 'Tegangan Rel F-F', ujung: 'Tegangan Ujung JTR', ground: 'Grounding' };
export const garduTone = col => {
  if (!col || col.line !== 0) return '';
  const n = String(col.name ?? col.label ?? '').toLowerCase();
  if (/tegangan\s+rel\b/.test(n)) return /\b[rst]\s*-\s*[rst]\b/.test(n) ? 'relff' : 'relfn';
  if (/tegangan\s+ujung/.test(n)) return 'ujung';
  if (/grounding|pentanahan|arr?ester/.test(n)) return 'ground';
  return '';
};
const topicKeys = cols => {
  const out = new Map();
  for (const c of cols) if (garduTone(c)) out.set(c.code, garduTone(c));
  const rest = cols.filter(c => c.line === 0 && !out.has(c.code));
  for (const key of new Set(rest.map(c => c.unit))) {
    const group = rest.filter(c => c.unit === key);
    const counts = new Map();
    for (const c of group) counts.set(twoWords(c), (counts.get(twoWords(c)) || 0) + 1);
    const split = counts.size > 1 && [...counts.values()].every(n => n >= 2);
    for (const c of group) out.set(c.code, split ? twoWords(c) : '');
  }
  return out;
};
const toneTitle = (tone, prefix) => (tone === 'ground' ? prefix || TONE_TITLE.ground : TONE_TITLE[tone]);
const phaseOf = sub => (/^netral$/i.test(sub) ? 'N' : ((/^([RSTN])(-[RSTN0])?$/.exec(sub) || [])[1] || ''));
export const unitLabel = u => (/^ohm$/i.test(String(u ?? '')) ? 'Ω' : u);
export const headerPlan = ordered => {
  const blocks = [];
  const topics = topicKeys(ordered);
  for (const col of ordered) {
    const last = blocks[blocks.length - 1];
    const topic = col.line === 0 ? topics.get(col.code) : '';
    if (last && last.line === col.line && last.unit === col.unit && last.topic === topic) last.cols.push(col);
    else blocks.push({ line: col.line, unit: col.unit, topic, cols: [col] });
  }
  const firstUnit = {};
  for (const b of blocks) if (!(b.line in firstUnit)) firstUnit[b.line] = b.unit;
  return blocks.map(b => {
    const names = b.cols.map(c => c.name ?? c.label);
    const subs = shortLabels(names);
    const topic = b.cols.length > 1 ? prefixWords(names) : names[0];
    const tone = b.line === 0 && TONE_TITLE[b.topic] ? b.topic : '';
    const title = b.line === 0 ? (tone ? toneTitle(tone, topic) : topic || 'Gardu')
      : b.unit === firstUnit[b.line] ? `Jurusan ${b.line}` : `Jurusan ${b.line} · ${topic}`;
    const sub = i => (b.cols.length > 1 ? subs[i] : tone && tone !== 'ground' ? (words(names[i]).at(-1) || '') : '');
    return { line: b.line, title, tone, unit: unitLabel(b.unit), span: b.cols.length,
      cells: b.cols.map((c, i) => ({ code: c.code, line: c.line, sub: sub(i), tone,
        unit: '', phase: phaseOf(b.cols.length > 1 ? subs[i] : sub(i)) })) };
  });
};
/** 9d-3: one readable status per row (label + tone) for the Status column. */
export const rowState = ({ verified, conflict, queue, filled }) => {
  if (conflict) return { label: 'Konflik · lihat', tone: 'danger' };
  if (verified) return { label: 'Terkunci (verified)', tone: 'muted' };
  const q = String(queue || '');
  if (q === 'menyimpan') return { label: 'Menyimpan…', tone: 'warn' };
  if (q === 'belum disimpan') return { label: 'Belum disimpan', tone: 'warn' };
  if (q.startsWith('tersimpan')) return { label: 'Tersimpan ' + q.slice(10).slice(0, 5), tone: 'ok' };
  if (q.startsWith('gagal') || q === 'sesi berakhir' || q === 'ada konflik') return { label: q[0].toUpperCase() + q.slice(1), tone: 'danger' };
  return filled ? { label: 'Tersimpan', tone: 'ok' } : { label: 'Belum diisi', tone: 'muted' };
};
/** Group chips are multi-select; empty selection means every active param. */
export const codesForGroups = (groups, chosen) =>
  chosen.length ? groups.filter(g => chosen.includes(g.name)).flatMap(g => g.codes) : null;
export const summarizeRows = states => {
  const n = t => states.filter(s => s.tone === t).length;
  return { saved: states.filter(s => s.label.startsWith('Tersimpan')).length, saving: n('warn'),
    conflict: states.filter(s => s.label.startsWith('Konflik')).length,
    empty: states.filter(s => s.label === 'Belum diisi').length };
};
/** Mobile form: one card per jurusan (or gardu), split by unit, rows labelled R/S/T/N with phase. */
export const mobileSections = (params, lineCount) => {
  const cols = orderColumns(columnsFromParams(params, null), lineCount);
  const topics = topicKeys(cols);
  const topicOf = c => (c.line === 0 ? topics.get(c.code) : '');
  const out = [];
  for (const line of [...new Set(cols.map(c => c.line))]) {
    const inLine = cols.filter(c => c.line === line);
    for (const key of [...new Set(inLine.map(c => c.unit + '|' + topicOf(c)))]) {
      const group = inLine.filter(c => c.unit + '|' + topicOf(c) === key);
      const unit = group[0].unit;
      const names = group.map(c => c.name ?? c.label);
      const subs = shortLabels(names);
      const topic = group.length > 1 ? prefixWords(names) : names[0];
      const tone = line === 0 && TONE_TITLE[topicOf(group[0])] ? topicOf(group[0]) : '';
      const title = line === 0 ? (tone ? toneTitle(tone, topic) : topic || 'Gardu') : `Jurusan ${line}`;
      out.push({ key: `${line}:${key}`, line, tone, unit: unitLabel(unit), title, topic: line === 0 ? '' : topic,
        rows: group.map((c, i) => ({ code: c.code, line: c.line, label: group.length > 1 ? subs[i] : names[i],
          phase: phaseOf(group.length > 1 ? subs[i] : (tone && tone !== 'ground' ? words(names[i]).at(-1) : '')) })) });
    }
  }
  return out;
};
export const filledCount = (rows, values, key) => rows.filter(r => String(values[key(r.code, r.line)] ?? '') !== '').length;
