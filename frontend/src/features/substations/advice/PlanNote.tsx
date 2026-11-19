import {useState} from 'react';
import {api} from '../../../api';
import {useScope} from '../scope';
import {canApply,planSummary} from './adviceView.mjs';

export type Plan={kind:'swap'|'move';target_id:number;target_code:string;line_no:number|null;portion:number|null;
 sides:{code:string;kva_before:number;kva_after:number}[];applied:{effective_on:string}|null};
type F={id:number;type_code:string;status:string;version:number;plan?:Plan|null};
const msg=(e:unknown)=>e instanceof Error?e.message:String(e);
export default function PlanNote({f,onDone}:{f:F;onDone:()=>void}){
 const scope=useScope(),[open,setOpen]=useState(false),[date,setDate]=useState(new Date().toISOString().slice(0,10)),[ok,setOk]=useState(false),[error,setError]=useState('');
 if(!f.plan)return null;const p=f.plan;
 async function apply(){try{await api(`/substations/advice-followups/${f.id}/apply-swap`,{method:'POST',body:JSON.stringify({effective_on:date,expected_version:f.version,confirm:ok})});setOpen(false);onDone()}catch(e){setError(msg(e))}}
 return <div className="adv-plan"><small>Rencana: {planSummary(p)}.{p.applied&&` Sudah diterapkan ke master (berlaku ${p.applied.effective_on}).`}</small>
  {canApply(f,!!scope?.can_manage_master)&&!open&&<button className="btn secondary sm" onClick={()=>setOpen(true)}>Terapkan ke master…</button>}
  {open&&<div className="gd-form adv-form"><p className="gd-full">Data trafo dua gardu akan <b>ditukar</b>: {p.sides.map(s=>`${s.code} ${s.kva_before} → ${s.kva_after} kVA`).join(' dan ')}. Merek, nomor seri, tap, dan fase ikut bertukar. Pengukuran lama tidak berubah; ukur ulang kedua gardu agar status di Analisa mengikuti trafo baru.</p>
   <label>Berlaku sejak<input type="date" value={date} max={new Date().toISOString().slice(0,10)} onChange={e=>setDate(e.target.value)}/></label>
   <label className="adv-check"><input type="checkbox" checked={ok} onChange={e=>setOk(e.target.checked)}/> Pekerjaan fisik sudah dilakukan</label>
   {error&&<p className="gd-error gd-full" role="alert">{error}</p>}
   <div className="gd-full gd-actions"><button className="btn secondary sm" onClick={()=>setOpen(false)}>Batal</button><button className="btn primary sm" disabled={!ok||!date} onClick={()=>void apply()}>Terapkan</button></div></div>}</div>;
}
