import {useState} from 'react';
import {api,num} from '../../../api';
import {ageText,excludedLines,pct,rangeText,splitOptions} from './adviceView.mjs';
import type {Advice,MoveOpt,Pick,SwapOpt,Target} from './types';
import ReviewDrawer from './ReviewDrawer';
import './advice.css';

const msg=(e:unknown)=>e instanceof Error?e.message:String(e);
const RADII=[['','Semua jarak'],['1','Dalam 1 km'],['3','Dalam 3 km'],['5','Dalam 5 km'],['10','Dalam 10 km']];
const who=(t:Target)=>`${t.code} · ${num(t.kva,0)} kVA · ${t.distance_km==null?'':num(t.distance_km,2)+' km'}`;
const meas=(t:Target)=>`sesi ${t.session} ${t.measured_on}${t.state==='draft'?' (draf)':''}, ${ageText(t.age_days)}`;
export default function AdviceBox({stationId,measurementId,canCreate,onChange}:{stationId:number;measurementId:number|null;canCreate:boolean;onChange?:()=>void}){
 const [data,setData]=useState<Advice|null>(null),[radius,setRadius]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[pick,setPick]=useState<Pick|null>(null);
 async function load(r=radius){setBusy(true);setError('');
  try{setData(await api<Advice>(`/substations/advice/${stationId}?`+new URLSearchParams({...(r?{radius_km:r}:{}),...(measurementId?{measurement_id:String(measurementId)}:{})})))}catch(e){setError(msg(e))}finally{setBusy(false)}}
 const swap=splitOptions<SwapOpt>(data?.swap),move=splitOptions<MoveOpt>(data?.move);
 const ex=excludedLines(data?.excluded);
 return <div className="adv">
  <p className="gd-muted">Gardu ini overload. Sistem dapat menyarankan tukar trafo atau pindah beban ke gardu lain dalam ULP yang sama, lengkap dengan perkiraan sebelum dan sesudah.</p>
  <div className="adv-bar"><select aria-label="Jarak kandidat" value={radius} onChange={e=>{setRadius(e.target.value);if(data)void load(e.target.value)}}>{RADII.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select>
   <button className="btn secondary sm" disabled={busy} onClick={()=>void load()}>{busy?'Menghitung…':data?'Hitung ulang':'Lihat saran'}</button></div>
  {error&&<p className="gd-error" role="alert">{error}</p>}
  {data&&!data.available&&<p className="adv-warn" role="status">{data.reason}</p>}
  {data&&data.available&&data.overload===false&&<p className="gd-muted">{data.reason}</p>}
  {data?.basis&&data.overload&&<p className="adv-basis">Dasar: pengukuran sesi {data.basis.session} {data.basis.measured_on} ({data.basis.state==='draft'?'draf':'terverifikasi'}, {ageText(data.basis.age_days)}), beban {pct(data.basis.persen)} pada trafo {num(data.basis.kva,0)} kVA.
   {data.basis.state==='draft'&&' Pengukuran ini belum diverifikasi.'}{data.basis.kva_changed&&' Kapasitas trafo sekarang berbeda dari saat pengukuran.'}</p>}
  {data?.overload&&<>
   <h5>Tukar trafo</h5>
   {!data.swap.length&&<p className="gd-muted">Tidak ada gardu kandidat dengan fase yang sama.</p>}
   {swap.ok.map(o=><div key={o.target.id} className="adv-opt"><div><b>{who(o.target)}</b><small>{meas(o.target)}</small>
     <span>Sesudah: gardu ini {pct(o.x_after)}, {o.target.code} {pct(o.z_after)}</span></div>
     <button className="btn primary sm" onClick={()=>setPick({kind:'swap',target:o.target})}>Tinjau</button></div>)}
   {!swap.ok.length&&!!swap.no.length&&<p className="gd-muted">Belum ada tukar trafo yang membuat kedua gardu aman.</p>}
   {!!swap.no.length&&<details><summary>{swap.no.length} kandidat belum memenuhi</summary>{swap.no.map(o=><p key={o.target.id} className="adv-no"><b>{o.target.code}</b> ({num(o.target.kva,0)} kVA): {o.reason}</p>)}</details>}
   <h5>Pindah beban</h5>
   {!data.move.length&&<p className="gd-muted">Tidak ada jurusan yang dapat dipindah atau gardu tujuan yang sesuai.</p>}
   {move.ok.map(o=><div key={`${o.target.id}-${o.line_no}`} className="adv-opt"><div><b>{o.line_label} → {who(o.target)}</b><small>{meas(o.target)}, beban sekarang {pct(o.target.persen_now)}</small>
     <span>Porsi yang layak: <b>{rangeText(o)}</b> dari arus jurusan ini</span></div>
     <button className="btn primary sm" onClick={()=>setPick({kind:'move',target:o.target,line_no:o.line_no,line_label:o.line_label,range:{p_min:o.p_min!,p_max:o.p_max!}})}>Tinjau</button></div>)}
   {!move.ok.length&&!!move.no.length&&<p className="gd-muted">Belum ada pemindahan beban yang membuat kedua gardu aman.</p>}
   {!!move.no.length&&<details><summary>{move.no.length} kemungkinan belum memenuhi</summary>{move.no.map(o=><p key={`${o.target.id}-${o.line_no}`} className="adv-no"><b>{o.line_label} → {o.target.code}</b>: {o.reason}</p>)}</details>}
   {!!ex.length&&<p className="adv-ex">Tidak diperhitungkan: {ex.join('; ')}.</p>}
   <ul className="adv-disc">{data.disclaimer.map(d=><li key={d}>{d}</li>)}</ul></>}
  {pick&&<ReviewDrawer stationId={stationId} measurementId={measurementId} pick={pick} canCreate={canCreate} onClose={()=>setPick(null)} onCreated={()=>{setPick(null);onChange?.();window.dispatchEvent(new Event('gardu-followup-changed'))}}/>}
 </div>;
}
