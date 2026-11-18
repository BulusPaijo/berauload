/** 9d-5: example sentence for the finding picker ("gardu dengan X ATAU Y"). */
export function findingSentence(names, mode) {
  const list = names.filter(Boolean);
  if (!list.length) return { lead: 'Belum ada temuan dipilih', parts: [], join: '', tail: 'semua gardu ikut, temuan tidak menyaring.' };
  const join = mode === 'all' ? 'DAN' : 'ATAU';
  const tail = list.length < 2 ? '' : mode === 'all'
    ? 'gardu harus punya semua temuan ini sekaligus.' : 'cukup satu temuan saja yang cocok.';
  return { lead: 'Gardu dengan', parts: list, join, tail };
}
export const findingText = (names, mode) => {
  const s = findingSentence(names, mode);
  return s.parts.length ? `${s.lead} ${s.parts.join(` ${s.join} `)}${s.tail ? ' — ' + s.tail : ''}` : `${s.lead} — ${s.tail}`;
};
