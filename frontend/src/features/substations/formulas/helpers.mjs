export const originLabel = row => row.origin === 'custom' ? 'Kustom'
  : row.default_expression && row.expression !== row.default_expression ? 'Diubah' : 'Bawaan';
export function insertToken(text, token, start, end) {
  const before = text.slice(0, start), after = text.slice(end);
  return {value: before + token + after, caret: start + token.length};
}
export const displayValue = (value, digits = 1, incomplete = false) =>
  (value === null || value === undefined ? '—'
    : new Intl.NumberFormat('id-ID', {maximumFractionDigits: digits}).format(value))
    + (incomplete ? ' ⚠ Tidak lengkap' : '');
export const errorMessage = reason => typeof reason === 'string'
  ? reason : reason?.message || 'Gagal memeriksa rumus';

export const recalcDecision = status => status.busy ? 'retry' : (!status.remaining || !status.processed) ? 'stop' : 'continue';
export function orderedCodes(rows,code,delta) {
 const ordered=[...rows].sort((a,b)=>a.display_order-b.display_order||a.id-b.id).map(v=>v.code);
 const index=ordered.indexOf(code),target=index+delta;
 if(index<0||target<0||target>=ordered.length)return ordered;
 [ordered[index],ordered[target]]=[ordered[target],ordered[index]];
 return ordered;
}
/** 9d-5 drag & drop: move `from` to the slot of `to` (others shift), by display order. */
export function dragCodes(rows,from,to) {
 const ordered=[...rows].sort((a,b)=>a.display_order-b.display_order||a.id-b.id).map(v=>v.code);
 const i=ordered.indexOf(from),j=ordered.indexOf(to);
 if(i<0||j<0||i===j)return ordered;
 ordered.splice(j,0,...ordered.splice(i,1));
 return ordered;
}
