import {useEffect,useState} from 'react';
import {api,activeUnitId} from '../../../api';
import type {Followup} from '../detail/FollowupBox';
import {followTone} from '../detail/detail.mjs';
import './work.css';

type Row=Followup&{code:string;name:string;priority:string};
type Resp={total:number;items:Row[];counts:Record<string,number>};
const STATUSES=['terbuka','dikerjakan','selesai','batal'];
const msg=(e:unknown)=>e instanceof Error?e.message:String(e);
export default function WorkList({canEdit,onOpenStation}:{canEdit:boolean;onOpenStation:(code:string)=>void}){
 const [status,setStatus]=useState<string[]>(['terbuka','dikerjakan']),[type,setType]=useState(''),[text,setText]=useState(''),[page,setPage]=useState(1);
 const [data,setData]=useState<Resp|null>(null),[types,setTypes]=useState<{code:string;name:string}[]>([]),[picked,setPicked]=useState<number[]>([]);
 const [bulkStatus,setBulkStatus]=useState(''),[bulkWho,setBulkWho]=useState(''),[error,setError]=useState(''),[notice,setNotice]=useState(''),[tick,setTick]=useState(0);
 const unit=activeUnitId();
 useEffect(()=>{api<{code:string;name:string}[]>('/substations/followups/types').then(setTypes).catch(()=>{});},[]);
 useEffect(()=>{const q=new URLSearchParams({page:String(page),page_size:'50'});status.forEach(s=>q.append('status',s));if(type)q.set('type_code',type);if(text)q.set('text',text);
  let live=true;api<Resp>('/substations/followups?'+q).then(r=>{if(live){setData(r);setPicked([]);setError('')}}).catch(e=>live&&setError(msg(e)));return()=>{live=false}},[status,type,text,page,unit,tick]);
 async function bulk(){if(!picked.length||(!bulkStatus&&!bulkWho))return;
  try{const r=await api<{updated:number;skipped:number[]}>('/substations/followups/bulk',{method:'POST',body:JSON.stringify({ids:picked,status:bulkStatus||null,assignee:bulkWho||null})});
   setNotice(`${r.updated} tindak lanjut diperbarui`+(r.skipped.length?`, ${r.skipped.length} dilewati (bukan unit aktif)`:''));setBulkStatus('');setBulkWho('');setTick(x=>x+1);}catch(e){setError(msg(e))}}
 const today=new Date().toISOString().slice(0,10);
 return <div className="wk">
  <header className="wk-head"><div><div className="substation-kicker">PENGUKURAN GARDU · DAFTAR KERJA</div><h2>Tindak lanjut</h2><p>Semua pekerjaan dari hasil pengukuran. Ubah status di sini atau di panel rincian gardu. Tidak ada yang dihapus; gunakan Batal.</p></div></header>
  <div className="wk-tabs" role="group" aria-label="Status">{STATUSES.map(s=>{const on=status.includes(s);
   return <button key={s} aria-pressed={on} className={'wk-tab'+(on?' on':'')} onClick={()=>{setPage(1);setStatus(on?status.filter(x=>x!==s):[...status,s])}}><span>{s}</span><b>{data?.counts[s]??0}</b></button>})}</div>
  <div className="wk-filters"><input placeholder="Cari gardu atau catatan" value={text} maxLength={120} onChange={e=>{setPage(1);setText(e.target.value)}}/>
   <select value={type} onChange={e=>{setPage(1);setType(e.target.value)}}><option value="">Semua jenis</option>{types.map(t=><option key={t.code} value={t.code}>{t.name}</option>)}</select>
   {canEdit&&picked.length>0&&<div className="wk-bulk"><b>{picked.length} dipilih</b><select aria-label="Ubah status" value={bulkStatus} onChange={e=>setBulkStatus(e.target.value)}><option value="">Status…</option>{STATUSES.map(s=><option key={s} value={s}>{s}</option>)}</select>
    <input aria-label="Penanggung jawab" placeholder="Penanggung jawab" value={bulkWho} onChange={e=>setBulkWho(e.target.value)}/><button className="btn primary sm" disabled={!bulkStatus&&!bulkWho} onClick={()=>void bulk()}>Terapkan</button></div>}</div>
  {error&&<div className="notice error" role="alert">{error}</div>}{notice&&<div className="notice info" role="status">{notice}</div>}
  <div className="wk-table"><table><thead><tr>{canEdit&&<th><input type="checkbox" aria-label="Pilih semua" checked={!!data?.items.length&&data.items.every(r=>picked.includes(r.id))} onChange={e=>setPicked(e.target.checked?(data?.items??[]).map(r=>r.id):[])}/></th>}
   <th>Gardu</th><th>Jenis</th><th>Prioritas</th><th>Penanggung jawab</th><th>Target</th><th>Status</th><th>Catatan</th></tr></thead>
   <tbody>{data?.items.map(r=><tr key={r.id}>{canEdit&&<td><input type="checkbox" aria-label={'Pilih '+r.code} checked={picked.includes(r.id)} onChange={e=>setPicked(p=>e.target.checked?[...p,r.id]:p.filter(x=>x!==r.id))}/></td>}
    <td><button className="an-link" onClick={()=>onOpenStation(r.code)}>{r.code}</button><small>{r.name}</small></td><td>{r.type_name}</td>
    <td><span className={'wk-pri wk-'+r.priority}>{r.priority}</span></td><td>{r.assignee??<span className="an-dim">—</span>}</td>
    <td className={r.due_on&&r.due_on<today&&['terbuka','dikerjakan'].includes(r.status)?'wk-late':''}>{r.due_on??'—'}</td>
    <td><span className={'gd-status gd-'+followTone(r.status)}>{r.status}</span></td><td className="wk-note">{r.note??''}</td></tr>)}
   {!data?.items.length&&<tr><td colSpan={8}><div className="an-empty"><b>Tidak ada tindak lanjut pada filter ini</b><span>Buat tindak lanjut dari panel rincian gardu di Analisa atau Peta.</span></div></td></tr>}</tbody></table></div>
  <div className="gx-pager"><span>{data?.total??0} tindak lanjut</span><button className="btn secondary sm" disabled={page<=1} onClick={()=>setPage(page-1)}>‹ Sebelumnya</button><button className="btn secondary sm" disabled={!data||page*50>=data.total} onClick={()=>setPage(page+1)}>Berikutnya ›</button></div>
 </div>;
}
