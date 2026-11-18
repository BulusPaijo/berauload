export const validPoint = p => Number.isFinite(Number(p.lat)) && Number.isFinite(Number(p.lon)) &&
  p.lat !== null && p.lon !== null && Math.abs(Number(p.lat)) <= 90 && Math.abs(Number(p.lon)) <= 180;
export const markerKind = marker => ['circle','square','triangle','diamond','star'].includes(marker)?marker:'circle';
export const escapeText = text => String(text??'').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
export const categoriesLegend = (rules, group) => rules.filter(r=>r.active&&r.kind==='category'&&
  (r.group_name===group||!group)).map(r=>({code:r.code,name:r.name,color:r.color,marker:markerKind(r.marker)}));
export function clusterPoints(points,project,cell=54){
 const groups=new Map();
 for(const p of points.filter(validPoint)){
  const pos=project(p.lat,p.lon),key=`${Math.floor(pos.x/cell)}:${Math.floor(pos.y/cell)}`;
  const group=groups.get(key);
  if(group){group.members.push(p);group.lat+=Number(p.lat);group.lon+=Number(p.lon);}
  else groups.set(key,{members:[p],lat:Number(p.lat),lon:Number(p.lon)});
 }
 return [...groups.values()].map(g=>({...g,lat:g.lat/g.members.length,lon:g.lon/g.members.length}));
}
const colorSteps=['#2d72ba','#07896c','#e58a00','#b62823'];
export function gradedColor(value,breaks){
 if(value===null||value===undefined||!Number.isFinite(Number(value)))return '#89949a';
 const index=breaks.filter(bound=>Number(value)>bound).length;
 return colorSteps[Math.min(index,colorSteps.length-1)];
}
export function quartiles(numbers){
 const xs=numbers.filter(v=>v!==null&&v!==undefined&&Number.isFinite(Number(v))).map(Number).sort((a,b)=>a-b);
 return xs.length?[.25,.5,.75].map(q=>xs[Math.min(xs.length-1,Math.floor(q*(xs.length-1)))]) : [];
}
export function colorAndShape(point,mode,group,rules,quantiles=[]){
 if(mode==='umur')return {color:gradedColor(point.age_days,quantiles),marker:'circle'};
 if(mode.startsWith('column:'))return {color:gradedColor(point.columns?.[mode.slice(7)]?.value,quantiles),marker:'square'};
 const chosen=point.categories?.find(r=>!group||r.group_name===group)??point.category;
 const rule=rules.find(r=>r.code===chosen?.code&&r.kind==='category'&&
    (!group||r.group_name===group));
 return {color:rule?.color||'#89949a',marker:markerKind(rule?.marker||point.category?.marker)};
}
export function withinNearest(points,lat,lon,limit=8){
 const R=6371,rad=x=>x*Math.PI/180;
 return points.filter(validPoint).map(p=>{
  const dLat=rad(p.lat-lat),dLon=rad(p.lon-lon);
  const a=Math.sin(dLat/2)**2+Math.cos(rad(lat))*Math.cos(rad(p.lat))*Math.sin(dLon/2)**2;
  return {...p,distance_km:2*R*Math.asin(Math.min(1,Math.sqrt(a)))};
 }).sort((a,b)=>a.distance_km-b.distance_km).slice(0,limit);
}
export const sharedURL=(tab,filter)=>{
 const q=new URLSearchParams(filter);q.set('gardu_tab',tab);return '?'+q.toString();
};
