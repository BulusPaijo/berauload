import {useEffect,useState} from 'react';
import {api,apiFetch,activeUnitId,csrf,downloadApi} from '../../../api';
import './work.css';

type Cover={start:string;end:string;stale_days:number;items:{unit_id:number;unit:string;level:string;total:number;measured:number;never:number;stale:number;percent:number|null}[];total:{total:number;measured:number;never:number;stale:number;percent:number|null}};
type Late={days:number;total:number;items:{id:number;code:string;name:string;feeder:string|null;power_kva:number;line_count:number;last_measured_on:string|null;age_days:number|null}[]};
const msg=(e:unknown)=>e instanceof Error?e.message:String(e);
const iso=(d:Date)=>d.toISOString().slice(0,10);
export default function MonitoringPage({canInput,onNavigate}:{canInput:boolean;onNavigate:(tab:string,id?:number|string)=>void}){
 const now=new Date();
 const [start,setStart]=useState(iso(new Date(now.getTime()-89*864e5))),[end,setEnd]=useState(iso(now));
 const [cover,setCover]=useState<Cover|null>(null),[late,setLate]=useState<Late|null>(null),[days,setDays]=useState(''),[page,setPage]=useState(1);
 const [picked,setPicked]=useState<number[]>([]),[error,setError]=useState('');const unit=activeUnitId();
 useEffect(()=>{api<Cover>(`/substations/monitoring/coverage?start=${start}&end=${end}`).then(setCover).catch(e=>setError(msg(e)))},[start,end,unit]);
 useEffect(()=>{api<Late>(`/substations/monitoring/unmeasured?page=${page}&page_size=50${days?'&days='+days:''}`).then(r=>{setLate(r);setPicked([])}).catch(e=>setError(msg(e)))},[days,page,unit]);
 async function sheet(format:'pdf'|'xlsx'){if(!picked.length)return;
  try{const r=await apiFetch('/api/substations/monitoring/worksheet',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({ids:picked,format})});
   if(!r.ok)throw new Error((await r.json().catch(()=>({}))).detail||`HTTP ${r.status}`);
   const url=URL.createObjectURL(await r.blob()),a=document.createElement('a');a.href=url;a.download='Lembar_Kerja_Gardu.'+format;document.body.append(a);a.click();a.remove();URL.revokeObjectURL(url);}
  catch(e){setError(msg(e))}}
 const t=cover?.total;
 return <div className="wk">
  <header className="wk-head"><div><div className="substation-kicker">PENGUKURAN GARDU · PEMANTAUAN</div><h2>Pemantauan &amp; laporan</h2><p>Cakupan pengukuran per unit dan gardu yang perlu diukur. Hanya hitungan; tidak ada aturan wajib.</p></div>
   <div className="an-actions"><button className="btn secondary" onClick={()=>void downloadApi('/substations/monitoring/report?format=xlsx','Laporan_Gardu.xlsx').catch(e=>setError(msg(e)))}>Laporan Excel</button>
    <button className="btn primary" onClick={()=>void downloadApi('/substations/monitoring/report?format=pdf','Laporan_Gardu.pdf').catch(e=>setError(msg(e)))}>Laporan PDF</button></div></header>
  {error&&<div className="notice error" role="alert">{error}</div>}
  <section className="wk-card"><div className="wk-card-head"><h3>Cakupan pengukuran</h3><label>Dari<input type="date" value={start} onChange={e=>setStart(e.target.value)}/></label><label>Sampai<input type="date" value={end} onChange={e=>setEnd(e.target.value)}/></label></div>
   {t&&<div className="wk-kpis"><div><b>{t.total}</b><span>gardu aktif</span></div><div><b className="mk-ok">{t.measured}</b><span>diukur dalam rentang</span></div><div><b>{t.percent??'—'}%</b><span>cakupan</span></div>
    <div><b>{t.never}</b><span>belum pernah diukur</span></div><div><b>{t.stale}</b><span>terakhir &gt; {cover?.stale_days} hari</span></div></div>}
   <table className="wk-cover"><thead><tr><th>Unit</th><th>Gardu aktif</th><th>Diukur</th><th>Cakupan</th><th>Belum pernah</th><th>Lama</th></tr></thead>
    <tbody>{cover?.items.map(u=><tr key={u.unit_id}><td>{u.level.toUpperCase()} · {u.unit}</td><td>{u.total}</td><td>{u.measured}</td>
     <td><span className="wk-prog"><i style={{width:`${u.percent??0}%`}}/></span>{u.percent??'—'}%</td><td>{u.never}</td><td>{u.stale}</td></tr>)}</tbody></table></section>
  <section className="wk-card"><div className="wk-card-head"><h3>Perlu diukur ({late?.total??0})</h3>
   <label>Belum diukur lebih dari<select value={days} onChange={e=>{setPage(1);setDays(e.target.value)}}><option value="">{cover?.stale_days??180} hari (pengaturan)</option><option value="30">30 hari</option><option value="90">90 hari</option><option value="365">365 hari</option></select></label>
   <span className="wk-spacer"/>{picked.length>0&&<><b>{picked.length} dipilih</b><button className="btn secondary sm" onClick={()=>void sheet('pdf')}>Lembar kerja PDF</button><button className="btn secondary sm" onClick={()=>void sheet('xlsx')}>Lembar kerja Excel</button></>}
   {canInput&&<button className="btn primary sm" onClick={()=>onNavigate('input')}>Buka input massal</button>}</div>
   <table className="wk-cover"><thead><tr><th><input type="checkbox" aria-label="Pilih semua" checked={!!late?.items.length&&late.items.every(i=>picked.includes(i.id))} onChange={e=>setPicked(e.target.checked?(late?.items??[]).map(i=>i.id):[])}/></th><th>Gardu</th><th>Penyulang</th><th>kVA</th><th>Jurusan</th><th>Terakhir diukur</th><th>Umur</th></tr></thead>
    <tbody>{late?.items.map(i=><tr key={i.id}><td><input type="checkbox" aria-label={'Pilih '+i.code} checked={picked.includes(i.id)} onChange={e=>setPicked(p=>e.target.checked?[...p,i.id]:p.filter(x=>x!==i.id))}/></td>
     <td><b>{i.code}</b><small> {i.name}</small></td><td>{i.feeder??'—'}</td><td>{i.power_kva}</td><td>{i.line_count}</td><td>{i.last_measured_on??'Belum pernah'}</td><td>{i.age_days==null?'—':`${i.age_days} hari`}</td></tr>)}</tbody></table>
   <div className="gx-pager"><span>Halaman {page}</span><button className="btn secondary sm" disabled={page<=1} onClick={()=>setPage(page-1)}>‹</button><button className="btn secondary sm" disabled={!late||page*50>=late.total} onClick={()=>setPage(page+1)}>›</button></div></section>
 </div>;
}
