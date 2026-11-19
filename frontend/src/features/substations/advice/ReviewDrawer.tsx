import {useEffect,useState} from 'react';
import {api} from '../../../api';
import Drawer from '../ui/Drawer';
import {KIND_TITLE,clampPortion,linesRows,pct,rangeText,sideRows,sliderState} from './adviceView.mjs';
import type {Pick,Review,Side} from './types';

const msg=(e:unknown)=>e instanceof Error?e.message:String(e);
function SideCard({side,title}:{side:Side;title:string}){
 const col=side.after.category?.color??'#768994',lines=linesRows(side);
 return <section className="adv-card"><h4>{title} <b>{side.code}</b> <small>{side.name}</small></h4>
  <table className="adv-tbl"><thead><tr><th/><th>Sebelum</th><th>Sesudah</th></tr></thead><tbody>
   {sideRows(side).map(r=><tr key={r.label} className={r.changed?'chg':''}><th>{r.label}</th><td>{r.before}</td><td>{r.label==='Kategori'?<span className="adv-cat" style={{color:col,background:col+'1c'}}>{r.after}</span>:r.after}</td></tr>)}</tbody></table>
  <details><summary>Arus rata-rata per jurusan (A)</summary><table className="adv-tbl"><tbody>{lines.map(l=><tr key={l.line} className={l.changed?'chg':''}><th>Jurusan {l.line}</th>
   <td>{l.before==null?'—':l.before.toFixed(1)}</td><td>{l.after==null?'—':l.after.toFixed(1)}</td></tr>)}</tbody></table></details></section>;
}
export default function ReviewDrawer({stationId,measurementId,pick,canCreate,onClose,onCreated}:{stationId:number;measurementId:number|null;pick:Pick;canCreate:boolean;onClose:()=>void;onCreated:()=>void}){
 const [portion,setPortion]=useState(pick.range?.p_min??100),[data,setData]=useState<Review|null>(null),[error,setError]=useState(''),[saving,setSaving]=useState(false);
 const [form,setForm]=useState({priority:'sedang',assignee:'',due_on:'',note:''});
 useEffect(()=>{let live=true;const q=new URLSearchParams({kind:pick.kind,target_id:String(pick.target.id)});
  if(measurementId)q.set('measurement_id',String(measurementId));
  if(pick.kind==='move'){q.set('line',String(pick.line_no));q.set('portion',String(portion))}
  const t=setTimeout(()=>{api<Review>(`/substations/advice/${stationId}/review?${q}`).then(r=>{if(live){setData(r);setError('')}}).catch(e=>live&&setError(msg(e)))},pick.kind==='move'?150:0);
  return()=>{live=false;clearTimeout(t)}},[stationId,measurementId,pick,portion]);
 async function create(){setSaving(true);
  try{await api('/substations/advice-followups',{method:'POST',body:JSON.stringify({substation_id:stationId,measurement_id:measurementId,kind:pick.kind,target_id:pick.target.id,
   line_no:pick.line_no??null,portion:pick.kind==='move'?portion:null,priority:form.priority,assignee:form.assignee||null,due_on:form.due_on||null,note:form.note||null})});onCreated()}
  catch(e){setError(msg(e))}finally{setSaving(false)}}
 const state=sliderState(portion,data?.option);const src=data?.sides[0],dst=data?.sides[1];
 const title=pick.kind==='swap'?`Tukar trafo dengan ${pick.target.code}`:`Pindah beban: ${pick.line_label} ke ${pick.target.code}`;
 return <Drawer wide title={title} subtitle={`${KIND_TITLE[pick.kind]} · perkiraan sebelum dan sesudah`} onClose={onClose}
  footer={<><button className="btn secondary" onClick={onClose}>Tutup</button>
   <button className="btn primary" disabled={!canCreate||!data?.ok_after||saving} title={!canCreate?'Pilih ULP/KP pemilik gardu':!data?.ok_after?'Rencana ini belum membuat kedua gardu aman':''} onClick={()=>void create()}>Jadikan tindak lanjut</button></>}>
  {pick.kind==='move'&&<div className="adv-slider"><label>Porsi arus jurusan yang dipindah: <b>{portion}%</b>
    <input type="range" min={1} max={100} value={portion} onChange={e=>setPortion(clampPortion(e.target.value,pick.range))}/></label>
   <small className={'adv-range '+state.tone}>{data?.option.feasible?`Porsi yang membuat kedua gardu aman: ${rangeText(data.option)}`:data?.option.reason??''}</small>
   <small>Porsi di bawah 100% berarti sebagian cabang atau pelanggan jurusan itu; perlu survei lapangan.</small></div>}
  {error&&<p className="gd-error" role="alert">{error}</p>}
  {data&&src&&dst&&<>
   <div className={'adv-result '+(data.ok_after?'ok':'bad')} role="status">{data.ok_after?'Sesudah perubahan ini, kedua gardu tidak overload.':'Sesudah perubahan ini masih ada gardu yang overload.'}
    {' '}Gardu ini {pct(src.before.persen)} → {pct(src.after.persen)}; {dst.code} {pct(dst.before.persen)} → {pct(dst.after.persen)}.</div>
   <div className="adv-cards"><SideCard side={src} title="Gardu ini"/><SideCard side={dst} title="Gardu tujuan"/></div>
   <p className="gd-muted">Pengukuran gardu ini sesi {data.source.session} {data.source.measured_on}{data.source.state==='draft'?' (draf)':''}; gardu tujuan sesi {data.target.session} {data.target.measured_on}{data.target.state==='draft'?' (draf)':''}. Jarak garis lurus {data.target.distance_km??'—'} km.</p>
   {canCreate&&<div className="gd-form adv-form"><label>Prioritas<select value={form.priority} onChange={e=>setForm({...form,priority:e.target.value})}><option value="rendah">Rendah</option><option value="sedang">Sedang</option><option value="tinggi">Tinggi</option></select></label>
    <label>Target<input type="date" value={form.due_on} onChange={e=>setForm({...form,due_on:e.target.value})}/></label>
    <label className="gd-full">Penanggung jawab<input value={form.assignee} maxLength={150} onChange={e=>setForm({...form,assignee:e.target.value})} placeholder="Regu / nama"/></label>
    <label className="gd-full">Catatan (kosong = ringkasan otomatis)<textarea value={form.note} maxLength={2000} onChange={e=>setForm({...form,note:e.target.value})}/></label></div>}
   <ul className="adv-disc">{data.disclaimer.map(d=><li key={d}>{d}</li>)}</ul></>}
  {!data&&!error&&<p className="gd-muted">Menghitung…</p>}
 </Drawer>;
}
