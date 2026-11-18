export function feederStacks(summary,defs){
 const byId=new Map(defs.feeders.map(f=>[f.id,f.name]));const rows=new Map();
 for(const entry of summary.feeder_categories){
  const key=entry.feeder_id??0;
  if(!rows.has(key))rows.set(key,{feeder:byId.get(key)||'Tanpa penyulang',id:key});
  rows.get(key)[entry.category]=entry.count;
 }
 return [...rows.values()].sort((a,b)=>String(a.feeder).localeCompare(String(b.feeder),'id'));
}
export function scatterPairs(points,sessions){
 if(sessions.length<2)return [];
 return points.filter(p=>p.sessions[sessions[0]]!=null&&p.sessions[sessions[1]]!=null)
   .map(p=>({id:p.id,x:Number(p.sessions[sessions[0]]),y:Number(p.sessions[sessions[1]])}));
}
export function findingPareto(findings){return findings.filter(f=>f.count>0).sort((a,b)=>b.count-a.count||a.code.localeCompare(b.code));}
export function trendRows(points){
 const rows=new Map();
 for(const p of points){if(!rows.has(p.day))rows.set(p.day,{day:p.day});rows.get(p.day)[p.session]=p.value;}
 return [...rows.values()].sort((a,b)=>a.day.localeCompare(b.day));
}
export function encodeCsv(rows){
 if(!rows.length)return '\ufeff';const keys=[...new Set(rows.flatMap(r=>Object.keys(r)))];
 const safe=v=>{const s=String(v??'');const escaped=typeof v==='string'&&/^[=+@\-\t\r]/.test(s)?"'"+s:s;
  return '"'+escaped.replaceAll('"','""')+'"'};
 return '\ufeff'+[keys.map(safe).join(','),...rows.map(r=>keys.map(k=>safe(r[k])).join(','))].join('\r\n');
}
export function densityKey(userId){return `berauload:gardu_density:${userId}`;}
export function readDensity(storage,userId){try{return storage.getItem(densityKey(userId))==='compact'?'compact':'comfortable';}catch{return 'comfortable';}}
export function saveDensity(storage,userId,value){if(!['compact','comfortable'].includes(value))return;try{storage.setItem(densityKey(userId),value);}catch{}}
