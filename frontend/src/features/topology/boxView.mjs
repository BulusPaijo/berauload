/** Presentation-only calculations. No electrical thresholds or inferred status. */
export function rankRows(codes,values,units){
 if(!codes.length)return {rows:[],mixed:false};
 const kinds=new Set(codes.map(code=>units?.[code]||''));
 if(kinds.size>1)return {rows:[],mixed:true};
 const rows=codes.map(code=>({code,value:values?.[code]})).filter(row=>
  typeof row.value==='number'&&Number.isFinite(row.value));
 rows.sort((a,b)=>b.value-a.value||codes.indexOf(a.code)-codes.indexOf(b.code));
 return {rows,mixed:false};
}
export function availableCount(codes,values){
 return codes.filter(code=>typeof values?.[code]==='number'&&Number.isFinite(values[code])).length;
}
/** Split at NULL, preserving 0 and all 24 hour slots; svg polyline segments only. */
export function sparkSegments(points,width=195,height=34){
 const series=Array.from({length:24},(_,i)=>points?.find(p=>p.hour===i)?.value??null);
 const present=series.filter(v=>typeof v==='number'&&Number.isFinite(v));
 if(!present.length)return [];
 const min=Math.min(...present),max=Math.max(...present),span=max-min||1;
 const coordinate=(value,hour)=>[4+(hour/23)*(width-8),height-4-((value-min)/span)*(height-8)];
 const output=[];let current=[];
 series.forEach((value,hour)=>{
  if(typeof value!=='number'||!Number.isFinite(value)){
   if(current.length)output.push(current);
   current=[];return;
  }
  current.push(coordinate(value,hour));
 });
 if(current.length)output.push(current);
 return output;
}
