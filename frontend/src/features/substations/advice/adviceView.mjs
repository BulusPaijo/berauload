// Pure helpers for the 9e advice UI (no React). Numbers come from the server; nothing is recomputed here.
export const KIND_TITLE={swap:'Tukar trafo',move:'Pindah beban'};
const nf=(v,d=1)=>v==null?'—':Number(v).toLocaleString('id-ID',{minimumFractionDigits:d,maximumFractionDigits:d});
export const pct=v=>v==null?'—':`${nf(v,1)}%`;
export const rangeText=o=>o&&o.feasible&&o.p_min!=null?(o.p_min===o.p_max?`${o.p_min}%`:`${o.p_min}%–${o.p_max}%`):'';
export const ageText=days=>days==null?'':days<=0?'hari ini':`${days} hari lalu`;
export const EXCLUDED_TEXT={tanpa_koordinat:'tanpa koordinat',tanpa_pengukuran:'belum pernah diukur',tidak_dapat_dinilai:'arus belum lengkap',
 fase_berbeda_untuk_tukar:'beda fase (tidak untuk tukar trafo)',sudah_overload_untuk_pindah:'sudah overload (tidak untuk pindah beban)'};
export function excludedLines(excluded){
 return Object.entries(excluded??{}).filter(([,n])=>n>0).map(([k,n])=>`${n} gardu ${EXCLUDED_TEXT[k]??k}`);}
/** Keep the server order (feasible first); only split so infeasible ones can be folded away. */
export function splitOptions(list){const ok=[],no=[];for(const o of list??[])(o.feasible?ok:no).push(o);return {ok,no};}
export function clampPortion(value,range){
 const n=Math.round(Number(value));if(!Number.isFinite(n))return range?.p_min??1;
 const lo=1,hi=100;return Math.min(hi,Math.max(lo,n));}
export function sliderState(portion,option){
 if(!option||!option.feasible)return {inside:false,tone:'bad'};
 const inside=portion>=option.p_min&&portion<=option.p_max;return {inside,tone:inside?'ok':'bad'};}
export function sideRows(side){
 const rows=[['Kapasitas trafo',`${nf(side.kva_before,0)} kVA`,`${nf(side.kva_after,0)} kVA`,side.kva_before!==side.kva_after],
  ['Beban',`${nf(side.before.beban_kva)} kVA`,`${nf(side.after.beban_kva)} kVA`,side.before.beban_kva!==side.after.beban_kva],
  ['Persen beban',pct(side.before.persen),pct(side.after.persen),side.before.persen!==side.after.persen],
  ['Kategori',side.before.category?.name??'—',side.after.category?.name??'—',side.before.category?.code!==side.after.category?.code]];
 if(side.before.tak_seimbang!==undefined)rows.push(['Ketidakseimbangan',pct(side.before.tak_seimbang),pct(side.after.tak_seimbang),side.before.tak_seimbang!==side.after.tak_seimbang]);
 return rows.map(([label,before,after,changed])=>({label,before,after,changed}));}
export function linesRows(side){
 return side.lines_before.map((b,i)=>{const a=side.lines_after[i];
  return {line:b.line_no,before:avg(b),after:avg(a),changed:avg(b)!==avg(a)};});}
function avg(l){const v=[l.i_r,l.i_s,l.i_t];return v.some(x=>x==null)?null:(v[0]+v[1]+v[2])/3;}
export const planSummary=plan=>!plan?'':plan.kind==='swap'?`Tukar trafo dengan ${plan.target_code}`
 :`Pindah ${plan.portion}% jurusan ${plan.line_no} ke ${plan.target_code}`;
export const canApply=(f,canManage)=>!!(canManage&&f&&f.type_code==='tukar_trafo'&&f.plan&&f.plan.kind==='swap'&&!f.plan.applied&&f.status==='selesai');
