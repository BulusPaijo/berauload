import {useActionDialog} from './ActionDialog';
import {useEffect,useState} from 'react';
import {api,activeUnitId,downloadApi,isoWita} from '../../api';
import type {Definitions,Feeder,Page,Substation,Visit} from './types';
import VisitDetail from './detail/VisitDetail';
import type {VisitDetailData} from './detail/VisitDetail';
const msg=(e:unknown)=>e instanceof Error?e.message:String(e);
type Props={defs:Definitions;feeders:Feeder[];readonly:boolean;canVerify:boolean};
export default function VisitList({defs,feeders,readonly,canVerify}:Props){
 const {confirm:askConfirm,prompt:askText,dialog}=useActionDialog();
 const unitId=activeUnitId()??0;
 const [page,setPage]=useState(1),[total,setTotal]=useState(0),[items,setItems]=useState<Visit[]>([]);
 const [start,setStart]=useState(''),[end,setEnd]=useState(''),[session,setSession]=useState(''),[state,setState]=useState(''),[feeder,setFeeder]=useState('');
 const [selected,setSelected]=useState<number[]>([]),[detail,setDetail]=useState<VisitDetailData|null>(null);
 const [message,setMessage]=useState(''),[action,setAction]=useState('verify'),[reason,setReason]=useState(''),[change,setChange]=useState(''),[changeField,setChangeField]=useState('technician');
 const [file,setFile]=useState<File|null>(null),[preview,setPreview]=useState<any>(null),[mode,setMode]=useState('fill_empty');
 const load=async()=>{try{const p=new URLSearchParams({page:String(page),page_size:'50'});
  if(start)p.set('start',start);if(end)p.set('end',end);if(session)p.set('session',session);
  if(state)p.set('state',state);if(feeder)p.set('feeder_id',feeder);
  const result=await api<Page<Visit>>('/substations/measurements?'+p);
  setItems(result.items);setTotal(result.total);setSelected([]);
 }catch(e){setMessage(msg(e))}};
 useEffect(()=>{void load()},[page,start,end,session,state,feeder,unitId]);
 const open=async(id:number)=>{try{setDetail(await api<VisitDetailData>(`/substations/measurements/${id}`))}catch(e){setMessage(msg(e))}};
 const runAction=async()=>{if(!selected.length)return;
  if(action==='reopen'&&!reason.trim()){setMessage('Alasan membuka kembali wajib diisi');return;}
  if(!(await askConfirm(`Terapkan ${action} pada ${selected.length} pengukuran?`)))return;
  try{let changes:Record<string,unknown>|undefined;
   if(action==='update')changes={[changeField]:change};
   const result=await api<{results:any[]}>('/substations/measurements/actions',{
    method:'POST',body:JSON.stringify({ids:selected,action,reason,changes})});
   setMessage(result.results.map(r=>`#${r.id}: ${r.status}${r.reason?' - '+r.reason:''}`).join(' · '));
   await load();
  }catch(e){setMessage(msg(e))}};
 async function inspect(){if(!file)return;const form=new FormData();form.append('file',file);
  try{setPreview(await api('/substations/measurements/import/preview',{method:'POST',body:form}));setMessage('Belum ada perubahan pada database.');}
  catch(e){setMessage(msg(e))}}
 async function apply(){if(!preview||!(await askConfirm('Terapkan pengukuran dari Excel?')))return;
  try{const result=await api<any>('/substations/measurements/import/apply',{
   method:'POST',body:JSON.stringify({token:preview.token,mode})});
   setMessage(`Hasil impor: ${result.results.filter((r:any)=>r.status==='saved').length} tersimpan, ${result.results.filter((r:any)=>r.status==='error').length} gagal`);
   setPreview(null);await load();}catch(e){setMessage(msg(e))}}
 return <div className="substation-stack">{dialog}
  <div className="substation-controls"><label>Mulai<input type="date" value={start} onChange={e=>{setStart(e.target.value);setPage(1)}}/></label><label>Sampai<input type="date" value={end} onChange={e=>{setEnd(e.target.value);setPage(1)}}/></label>
   <label>Sesi<select value={session} onChange={e=>setSession(e.target.value)}><option value="">Semua</option>{defs.sessions.map(s=><option key={s.code} value={s.code}>{s.name}</option>)}</select></label>
   <label>Status<select value={state} onChange={e=>setState(e.target.value)}><option value="">Semua</option><option value="draft">Draft</option><option value="verified">Verified</option></select></label>
   <label>Penyulang<select value={feeder} onChange={e=>setFeeder(e.target.value)}><option value="">Semua</option>{feeders.map(f=><option value={f.id} key={f.id}>{f.name}</option>)}</select></label>
  </div>
  {message&&<div className="notice info">{message}</div>}
  <div className="scroll-table"><table><thead><tr><th><input type="checkbox" checked={!!items.length&&items.every(r=>selected.includes(r.id))} onChange={e=>setSelected(e.target.checked?items.map(v=>v.id):[])}/></th><th>Tanggal</th><th>Gardu</th><th>Sesi</th><th>Petugas</th><th>Status</th><th>Revisi</th><th>Aksi</th></tr></thead><tbody>{items.map(v=><tr key={v.id}><td><input type="checkbox" checked={selected.includes(v.id)} onChange={e=>setSelected(e.target.checked?[...selected,v.id]:selected.filter(id=>id!==v.id))}/></td><td>{v.measured_on}</td><td className="vl-gardu"><b>{v.substation_code??'#'+v.substation_id}</b><small>{v.substation_name??''}{v.unit_name?' · '+v.unit_name:''}</small></td><td>{defs.sessions.find(s=>s.code===v.session)?.name??v.session}</td><td>{v.technician||'—'}</td><td><span className={'vd-state '+v.state}>{v.state==='verified'?'Terverifikasi':'Draft'}</span></td><td>{v.revision}</td><td><button className="link-btn" onClick={()=>open(v.id)}>Detail & riwayat</button></td></tr>)}</tbody></table>{!items.length&&<div className="empty">Belum ada pengukuran pada filter ini.</div>}</div>
  <div className="substation-toolbar"><span>{total} pengukuran · halaman {page}</span><button className="btn secondary sm" disabled={page<=1} onClick={()=>setPage(page-1)}>Sebelumnya</button><button className="btn secondary sm" disabled={page*50>=total} onClick={()=>setPage(page+1)}>Berikutnya</button></div>
  {!readonly&&!!selected.length&&<div className="panel"><h3>Aksi massal ({selected.length})</h3><div className="substation-controls">
   <select value={action} onChange={e=>setAction(e.target.value)}><option value="verify" disabled={!canVerify}>Verifikasi</option><option value="reopen" disabled={!canVerify}>Buka kunci</option><option value="delete">Hapus draft</option><option value="update">Ubah petugas</option></select>
   {action==='reopen'&&<input placeholder="Alasan wajib" value={reason} onChange={e=>setReason(e.target.value)}/>}
   {action==='update'&&<><select value={changeField} onChange={e=>setChangeField(e.target.value)}><option value="technician">Petugas</option><option value="measured_on">Tanggal</option><option value="session">Sesi</option></select>{changeField==='session'?<select value={change} onChange={e=>setChange(e.target.value)}>{defs.sessions.filter(s=>s.active).map(s=><option key={s.code} value={s.code}>{s.name}</option>)}</select>:<input type={changeField==='measured_on'?'date':'text'} placeholder="Nilai baru" value={change} onChange={e=>setChange(e.target.value)}/>}</>}
   <button className="btn primary" onClick={runAction}>Konfirmasi aksi</button></div></div>}
  {detail&&<VisitDetail data={detail} defs={defs} onClose={()=>setDetail(null)}/>}
  {!readonly&&<div className="panel"><h3>Impor Pengukuran dari Excel</h3>
   <p>Unduh template, isi tanggal/sesi/jam dan nilai. Pratinjau tidak menulis ke database.</p>
   <button className="btn secondary" onClick={()=>void downloadApi('/substations/measurements/template?'+new URLSearchParams({day:start||isoWita(),session:session||'SIANG',...(feeder?{feeder_id:feeder}:{})}), 'pengukuran_gardu.xlsx')}>Unduh Template XLSX</button>
   <input type="file" accept=".xlsx,.csv" onChange={e=>setFile(e.target.files?.[0]||null)}/><button className="btn secondary" disabled={!file} onClick={inspect}>Pratinjau</button>
   {preview&&<><div className="scroll-table"><table><thead><tr><th>Baris</th><th>Gardu ID</th><th>Tanggal</th><th>Sesi</th><th>Validasi</th></tr></thead><tbody>{preview.rows.map((r:any)=><tr key={r.row}><td>{r.row}</td><td>{r.values.substation_id}</td><td>{r.values.measured_on}</td><td>{r.values.session}</td><td>{r.errors.join('; ')||'Sah'}</td></tr>)}</tbody></table></div>
    <label>Mode<select value={mode} onChange={e=>setMode(e.target.value)}><option value="fill_empty">Hanya sel kosong</option><option value="overwrite">Timpa draft (konfirmasi)</option></select></label>
    <button className="btn primary" onClick={apply}>Konfirmasi dan Import</button></>}
  </div>}
 </div>;
}
