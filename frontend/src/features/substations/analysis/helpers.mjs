const allowed = ['mode','start','end','session','feeder_id','unit_id','min_kva','max_kva',
  'category','finding_mode','state','status','text','numeric_code','numeric_op',
  'numeric_min','numeric_max','sort','desc','page','page_size'];
export const defaults = {mode:'terakhir',session:'tertinggi',sort:'code',desc:'false',page:'1',page_size:'50'};
export function fromQuery(search){
 const q=new URLSearchParams(search),out={...defaults};
 for(const key of allowed){if(q.has(key))out[key]=q.get(key)??'';}
 out.findings=q.getAll('findings').filter(Boolean);
 return out;
}
export function toQuery(state){
 const q=new URLSearchParams();
 for(const key of allowed){const value=state[key];if(value!==undefined&&value!==null&&value!==''){
  if(String(value)!==String(defaults[key]??''))q.set(key,String(value));
 }}
 for(const code of state.findings??[])q.append('findings',code);
 return q.toString();
}
export function chips(rules){return rules.filter(rule=>rule.active &&
  (rule.kind==='category'||rule.kind==='finding')).map(rule=>({
   code:rule.code,name:rule.name,kind:rule.kind,color:rule.color,group:rule.group_name}));}
export function valueText(value,digits=1,incomplete=false){
 const val=value===null||value===undefined?'—':new Intl.NumberFormat('id-ID',{
  maximumFractionDigits:digits}).format(value);
 return val+(incomplete?' ⚠':'');
}
export function direction(state,key){return state.sort===key?{
 sort:key,desc:state.desc==='true'?'false':'true'}:{sort:key,desc:'false'};}
export const defaultColumns=['code','feeder','power_kva','measured_on','reference','category','findings'];
export function applyView(view, definitions){
 const layout={...defaults,...view.layout,page:'1',findings:view.layout.findings??[]};
 if(!definitions)return layout;
 const rules=new Map(definitions.rules.filter(x=>x.active).map(x=>[x.code,x.kind]));
 const columns=new Set(definitions.columns.filter(x=>x.active).map(x=>x.code));
 const fields=new Set(definitions.fields.filter(x=>x.active).map(x=>'extra_'+x.code));
 const masters=new Set(['code','name','feeder','power_kva','brand','address','measured_on',
  'session','state','status','reference','category','findings']);
 const validColumn=(key)=>masters.has(key)||columns.has(key)||fields.has(key)||key==='followup'||(typeof key==='string'&&key.startsWith('sesi:'));
 if(layout.category&&layout.category!=='tidak_dapat_dinilai'&&rules.get(layout.category)!=='category')layout.category='';
 layout.findings=layout.findings.filter(x=>rules.get(x)==='finding');
 if(layout.numeric_code&&!columns.has(layout.numeric_code)){
  layout.numeric_code='';layout.numeric_op='';layout.numeric_min='';layout.numeric_max='';
 }
 if(!validColumn(layout.sort))layout.sort='code';
 if(Array.isArray(layout.columns))layout.columns=layout.columns.filter(validColumn);
 return layout;
}
export function serializeView(state,columns,widths){
 const layout={...state,columns,widths};delete layout.page;return layout;
}

/** 9d-3 default table columns (approved design): built from admin definitions, never hard-coded thresholds. */
export function designColumns(definitions){
 const have=new Set((definitions?.columns??[]).filter(c=>c.active).map(c=>c.code));
 return ['code','feeder','power_kva',...(definitions?.sessions??[]).map(s=>'sesi:'+s.code),'category',
  ...['tak_seimbang','v_ujung_min'].filter(c=>have.has(c)),'measured_on','followup'];
}
/** Calc columns that a finding rule refers to → mark the cell with × when that finding matched. */
export function findingColumns(rules){
 const out={};
 for(const r of rules.filter(x=>x.kind==='finding'&&x.active)){
  for(const code of String(r.expression).match(/[a-z_][a-z0-9_]*/g)??[]){(out[code]??=[]).push(r.code);}
 }
 return out;
}
