import {useEffect,useState} from 'react';
import {api} from '../../../api';
import {followTone} from './detail.mjs';

export type Followup={id:number;type_code:string;type_name:string;status:string;priority:string;assignee:string|null;due_on:string|null;note:string|null;version:number;substation_id:number};
type FType={code:string;name:string;active:boolean};
type Suggest={type_code:string;name:string;because:string[]};
const msg=(e:unknown)=>e instanceof Error?e.message:String(e);
const STATUSES=['terbuka','dikerjakan','selesai','batal'];
export default function FollowupBox({stationId,measurementId,canEdit,onChange}:{stationId:number;measurementId:number|null;canEdit:boolean;onChange?:()=>void}){
 const [items,setItems]=useState<Followup[]>([]),[types,setTypes]=useState<FType[]>([]),[sugs,setSugs]=useState<Suggest[]>([]);
 const [form,setForm]=useState<{type_code:string;priority:string;assignee:string;due_on:string;note:string}|null>(null),[error,setError]=useState('');
 const load=()=>Promise.all([api<{items:Followup[]}>(`/substations/followups?substation_id=${stationId}&page_size=20`),
  api<FType[]>('/substations/followups/types'),api<{suggestions:Suggest[]}>(`/substations/followups/suggest/${stationId}`+(measurementId?`?measurement_id=${measurementId}`:''))])
  .then(([f,t,s])=>{setItems(f.items);setTypes(t.filter(x=>x.active));setSugs(s.suggestions)}).catch(e=>setError(msg(e)));
 useEffect(()=>{setForm(null);void load()},[stationId,measurementId]);
 async function create(){if(!form)return;try{await api('/substations/followups',{method:'POST',body:JSON.stringify({...form,substation_id:stationId,measurement_id:measurementId,due_on:form.due_on||null})});
  setForm(null);await load();onChange?.();}catch(e){setError(msg(e))}}
 async function setStatus(f:Followup,status:string){try{await api(`/substations/followups/${f.id}`,{method:'PATCH',body:JSON.stringify({substation_id:f.substation_id,type_code:f.type_code,priority:f.priority,
  assignee:f.assignee,due_on:f.due_on,note:f.note,status,expected_version:f.version})});await load();onChange?.();}catch(e){setError(msg(e))}}
 const start=(code='')=>setForm({type_code:code||types[0]?.code||'',priority:'sedang',assignee:'',due_on:'',note:''});
 return <div className="gd-follow">
  {error&&<p className="gd-error" role="alert">{error}</p>}
  {items.map(f=><div key={f.id} className="gd-follow-item"><div><b>{f.type_name}</b><small>{[f.assignee,f.due_on&&`target ${f.due_on}`,f.priority!=='sedang'&&`prioritas ${f.priority}`].filter(Boolean).join(' · ')||'Belum ada penanggung jawab'}</small>{f.note&&<p>{f.note}</p>}</div>
   {canEdit?<select aria-label="Status tindak lanjut" className={'gd-status gd-'+followTone(f.status)} value={f.status} onChange={e=>void setStatus(f,e.target.value)}>{STATUSES.map(s=><option key={s} value={s}>{s}</option>)}</select>
    :<span className={'gd-status gd-'+followTone(f.status)}>{f.status}</span>}</div>)}
  {!items.length&&!form&&<p className="gd-muted">Belum ada tindak lanjut.</p>}
  {canEdit&&!form&&!!sugs.length&&<div className="gd-sugs"><span>Usulan dari temuan:</span>{sugs.slice(0,3).map(s=><button key={s.type_code} className="gd-sug" title={'Karena: '+s.because.join(', ')} onClick={()=>start(s.type_code)}>+ {s.name}</button>)}</div>}
  {canEdit&&!form&&<button className="btn secondary sm" onClick={()=>start()}>+ Buat tindak lanjut</button>}
  {form&&<div className="gd-form">
   <label>Jenis<select value={form.type_code} onChange={e=>setForm({...form,type_code:e.target.value})}>{types.map(t=><option key={t.code} value={t.code}>{t.name}</option>)}</select></label>
   <label>Prioritas<select value={form.priority} onChange={e=>setForm({...form,priority:e.target.value})}><option value="rendah">Rendah</option><option value="sedang">Sedang</option><option value="tinggi">Tinggi</option></select></label>
   <label>Penanggung jawab<input value={form.assignee} maxLength={150} onChange={e=>setForm({...form,assignee:e.target.value})} placeholder="Regu / nama"/></label>
   <label>Target<input type="date" value={form.due_on} onChange={e=>setForm({...form,due_on:e.target.value})}/></label>
   <label className="gd-full">Catatan<textarea value={form.note} maxLength={2000} onChange={e=>setForm({...form,note:e.target.value})}/></label>
   <div className="gd-full gd-actions"><button className="btn secondary sm" onClick={()=>setForm(null)}>Batal</button><button className="btn primary sm" disabled={!form.type_code} onClick={()=>void create()}>Simpan</button></div>
  </div>}
 </div>;
}
