/** Pure formatting for the per-hour topology viewer. No synthetic readings. */
export function formatMetric(value,decimals=2){
 if(value===null||value===undefined||!Number.isFinite(value))return '—';
 return new Intl.NumberFormat('id-ID',{maximumFractionDigits:Math.min(4,Math.max(0,decimals))}).format(value);
}
export function hourLabel(hour){return `${String(hour).padStart(2,'0')}:00`}
export function dayStatus(status){
 if(status==='final')return 'Final';
 if(status==='verified')return 'Terverifikasi';
 if(status==='draft')return 'Draft / belum difinalkan';
 return '—';
}
export function trendPoints(result,metric){
 const byHour=new Map((result?.series[metric]||[]).map(row=>[row.hour,row.value]));
 return Array.from({length:24},(_,hour)=>({
  jam:hourLabel(hour),nilai:byHour.has(hour)?(byHour.get(hour)??null):null,
 }));
}
