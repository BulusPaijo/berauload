import {useEffect,useState} from 'react';
import {api,activeUnitId,isoWita} from '../../api';
import type {Definitions,Page,Substation,Visit} from './types';
import {parseNumber,mobileSections,filledCount} from './grid.mjs';
import './mobile-form.css';
import GarduPicker from './GarduPicker';
import {useScope} from './scope';
import ResultPanel from './formulas/ResultPanel';
import type {CalcResults} from './formulas/types';
const msg=(e:unknown)=>e instanceof Error?e.message:String(e);
const key=(code:string,line:number)=>`${code}:${line}`;
export default function MobileVisitForm({defs,readonly,initialStationId}:{defs:Definitions;readonly:boolean;initialStationId?:number}){
 const unitId=activeUnitId()??0;
 const [gardus,setGardus]=useState<Substation[]>([]),[selected,setSelected]=useState(initialStationId??0);
 const [day,setDay]=useState(isoWita()),[session,setSession]=useState('SIANG');
 const [technician,setTechnician]=useState(''),[note,setNote]=useState('');
 const [values,setValues]=useState<Record<string,string>>({}),[visit,setVisit]=useState<Visit|null>(null);
 const [message,setMessage]=useState('');
 const [calculated,setCalculated]=useState<CalcResults|null>(null);
 const scope=useScope();
 useEffect(()=>{setGardus([]);if(initialStationId)api<{master:Substation}>(`/substations/master/${initialStationId}`).then(x=>setGardus([x.master])).catch(e=>setMessage(msg(e)));},[unitId,initialStationId]);
 useEffect(()=>{if(!selected)return;
  api<{items:Visit[]}>(`/substations/measurements/grid?day=${day}&session=${session}&ids=${selected}`).then(r=>{
   const entry=r.items[0]||null;setVisit(entry);setCalculated(null);
   if(entry)api<CalcResults>(`/substations/calculations/measurements/${entry.id}/results`).then(setCalculated).catch(()=>{});
   const byId=new Map(defs.params.map(p=>[p.id,p.code]));
   const result:Record<string,string>={};
   for(const val of entry?.values||[])result[key(byId.get(val.param_id)||'',val.line_no)]=
    val.flag?'@'+val.flag:val.value==null?'':String(val.value);
   setValues(result);
  }).catch(e=>setMessage(msg(e)))},[selected,day,session]);
 const gardu=gardus.find(x=>x.id===selected);
 async function save(){if(!gardu)return;
  try{const patches=Object.entries(values).map(([combined,raw])=>{
   const [code,line]=combined.split(':');return {code,line_no:Number(line),
    value:raw.startsWith('@')?null:parseNumber(raw),flag:raw.startsWith('@')?raw.slice(1):null};
  });
  const result=await api<{measurement:Visit,status:string;calculated:CalcResults}>('/substations/measurements',{
   method:'PUT',body:JSON.stringify({substation_id:selected,measured_on:day,session,
   technician,note,revision:visit?.revision??null,values:patches})});
  setVisit(result.measurement);setCalculated(result.calculated);setMessage(result.status==='unchanged'?'Tidak ada perubahan':'Pengukuran tersimpan');
  }catch(e){setMessage(msg(e))}}
 const locked=readonly||visit?.state==='verified';
 const sections=gardu?mobileSections(defs.params.filter(p=>p.active),gardu.line_count):[];
 const flags=defs.flags.filter(f=>f.active);
 const total=sections.reduce((n,s)=>n+s.rows.length,0),done=sections.reduce((n,s)=>n+filledCount(s.rows,values,key),0);
 const setCell=(cell:string,text:string)=>setValues(old=>({...old,[cell]:text}));
 return <div className="mf">
  <section className="mf-card mf-top">
   <div className="mf-field"><span>Gardu</span><GarduPicker value={gardu??null} allowed={scope?.data_unit_ids??[]} onPick={s=>{setGardus(g=>[s,...g.filter(x=>x.id!==s.id)]);setSelected(s.id)}}/></div>
   <div className="mf-row2"><label className="mf-field">Tanggal<input type="date" value={day} onChange={e=>setDay(e.target.value)}/></label>
   <label className="mf-field">Sesi<select value={session} onChange={e=>setSession(e.target.value)}>{defs.sessions.filter(s=>s.active).map(s=><option key={s.code} value={s.code}>{s.name}</option>)}</select></label></div>
   <label className="mf-field">Petugas<input value={technician} placeholder="Regu · nama" onChange={e=>setTechnician(e.target.value)} disabled={readonly}/></label>
  </section>
  {!gardu&&<p className="mf-hint">Pilih gardu untuk mulai mengisi. Hanya jurusan yang ada di gardu itu yang ditampilkan.</p>}
  {gardu&&<>
   <div className="mf-gardu"><div><b>{gardu.code}</b><span>{gardu.name} · {Number(gardu.power_kva)} kVA · {gardu.line_count} jurusan</span></div>
    <span className={'mf-badge'+(visit?.state==='verified'?' lock':'')}>{visit?.state==='verified'?'Terkunci':`${done}/${total} terisi`}</span></div>
   <div className="mf-legend" aria-hidden="true"><span><i className="mf-ph R">R</i>Fasa R</span><span><i className="mf-ph S">S</i>Fasa S</span><span><i className="mf-ph T">T</i>Fasa T</span><span><i className="mf-ph N">N</i>Netral</span></div>
   {sections.map(sec=>{const n=filledCount(sec.rows,values,key);
    return <details key={sec.key} className={"mf-card mf-sec mf-l"+sec.line+(sec.tone?" mf-t-"+sec.tone:"")} open={sec.line<=1||n>0}>
     <summary><span className="mf-sec-title">{sec.title}{sec.topic&&<small> · {sec.topic}</small>}<em>({sec.unit})</em></span><span className={'mf-count'+(n===sec.rows.length?' full':'')}>{n}/{sec.rows.length}</span></summary>
     {sec.rows.map(row=>{const cell=key(row.code,row.line),raw=values[cell]??'',flag=raw.startsWith('@')?raw.slice(1):'';
      return <div key={cell} className={'mf-line'+(row.phase?' ph-'+row.phase:'')+(flag?' flagged':'')}>
       <i className={'mf-ph '+(row.phase||'X')}>{row.phase||'•'}</i>
       <label className="mf-label" htmlFor={'mf-'+cell}>{row.label}</label>
       {flag?<button className="mf-flag" disabled={locked} onClick={()=>setCell(cell,'')} aria-label={`Hapus penanda ${flag}`}>{flags.find(f=>f.code===flag)?.name??flag} ✕</button>
        :<input id={'mf-'+cell} inputMode="decimal" enterKeyHint="next" disabled={locked} value={raw} placeholder="—" onChange={e=>setCell(cell,e.target.value)}/>}
       {!flag&&!locked&&flags.length>0&&<select className="mf-more" aria-label={`Penanda ${row.label}`} value="" onChange={e=>e.target.value&&setCell(cell,'@'+e.target.value)}><option value="">⋯</option>{flags.map(f=><option key={f.code} value={f.code}>{f.name}</option>)}</select>}
      </div>;})}
    </details>;})}
   <label className="mf-card mf-field">Catatan<textarea value={note} onChange={e=>setNote(e.target.value)} disabled={locked}/></label>
   <div className="mf-save"><span>{message||(locked?'Pengukuran terverifikasi tidak bisa diubah.':'Kosong berarti belum diukur, bukan nol.')}</span><button className="btn primary" disabled={locked} onClick={save}>Simpan</button></div>
  </>}
  <ResultPanel data={calculated}/>
 </div>
}
