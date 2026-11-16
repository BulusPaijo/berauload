/** Historical chart helpers. The only join key is hour; never fabricate values. */
export function comparisonAllowed(codes,units){
 return codes.length>1&&codes.every(code=>typeof units?.[code]==='string'&&units[code].trim())&&
  new Set(codes.map(code=>units[code])).size===1;
}
export function combinedTrendPoints(series,codes){
 return Array.from({length:24},(_,hour)=>{
  const row={jam:`${String(hour).padStart(2,'0')}:00`};
  for(const code of codes){
   const v=series?.series?.[code]?.find(point=>point.hour===hour)?.value;
   row[code]=typeof v==='number'&&Number.isFinite(v)?v:null;
  }
  return row;
 });
}
