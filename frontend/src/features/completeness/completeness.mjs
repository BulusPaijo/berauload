/** Presentation-only coverage helpers; no guessing missing data. */
export const basisLabel = basis => basis === 'system.load'
  ? 'dasar: beban sistem' : 'dasar: parameter input apa pun';
export const statusLetter = status => ({draft:'D',verified:'V',final:'F'})[status] || 'D';
export const cellLabel = cell => `${cell.filled_hours}/${cell.expected_hours} ${statusLetter(cell.status)}${cell.future?' (masa depan)':''}`;
export const coverageLabel = summary => summary.percent == null ? '—' : `${summary.percent.toLocaleString('id-ID',{maximumFractionDigits:2})}%`;
export const initialRange = (today) => {
 const date = new Date(`${today}T12:00:00Z`); date.setUTCDate(date.getUTCDate()-13);
 return [date.toISOString().slice(0,10), today];
};
