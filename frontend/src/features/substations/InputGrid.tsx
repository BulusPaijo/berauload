import {useEffect,useMemo,useRef,useState} from 'react';
import {api,apiFetch,setCSRF,activeUnitId,isoWita,downloadApi} from '../../api';
import ResultPanel from './formulas/ResultPanel';
import type {CalcResults} from './formulas/types';
import type {User} from '../../api';
import {HourQueue,readBackup,saveBackup} from '../input-form/autosave/core.mjs';
import {setDirty} from '../input-form/autosave/sessionActivity.mjs';
import {allowedCell,cellKey,columnsFromParams,orderColumns,headerPlan,nextCell,parseNumber,
  parsePaste,visitBackupKey,codesForGroups,rowState,summarizeRows} from './grid.mjs';
import GridTable from './GridTable';
import type {GridColumn} from './grid.mjs';
import type {Definitions,Feeder,Page,Substation,Visit} from './types';
import ConflictDialog from './ConflictDialog';
import './grid-table.css';

const storage=()=>{try{return localStorage}catch{return null}};
const msg=(e:unknown)=>e instanceof Error?e.message:String(e);
const apiError=async(r:Response)=>{const data=await r.json().catch(()=>({}));
 return data.detail||`HTTP ${r.status}`;};

type Props={user:User;defs:Definitions;feeders:Feeder[];readonly:boolean;onNavigate?:(tab:string)=>void};
export default function InputGrid({user,defs,feeders,readonly,onNavigate}:Props){
 const [day,setDay]=useState(isoWita()),[session,setSession]=useState('SIANG');
 const [feeder,setFeeder]=useState(''),[technician,setTechnician]=useState('');
 const [page,setPage]=useState(1),[rows,setRows]=useState<Substation[]>([]),[total,setTotal]=useState(0);
 const [selectedCalc,setSelectedCalc]=useState<{id:number;data:CalcResults}|null>(null);
 const [visits,setVisits]=useState<Record<number,Visit>>({});
 const [drafts,setDrafts]=useState<Record<string,string>>({});
 const [statuses,setStatuses]=useState<Record<number,string>>({});
 const [message,setMessage]=useState(''),[chosenGroups,setChosenGroups]=useState<string[]>([]);
 const [picked,setPicked]=useState<number[]>([]),[focusCell,setFocusCell]=useState<[number,number]|null>(null);
 const [backup,setBackup]=useState<any>(null),[otherTab,setOtherTab]=useState(false);
 const [conflict,setConflict]=useState<Record<number,Visit & {updated_by_name?:string|null}>>({});
 const [conflictCopy,setConflictCopy]=useState<Record<string,string>|null>(null);
 const [expired,setExpired]=useState(false),[login,setLogin]=useState({username:user.username,password:''});
 const [busy,setBusy]=useState(false),[lastEdit,setLastEdit]=useState<Record<string,string>|null>(null);
 const draftsRef=useRef<Record<string,string>>({}),visitsRef=useRef<Record<number,Visit>>({});
 const pendingRecovery=useRef(false);
 const unitId=activeUnitId()??0;
 const key=visitBackupKey(user.id,unitId,day,session);
 const params=defs.params.filter(p=>p.active);
 const maxLine=rows.reduce((m,r)=>Math.max(m,r.line_count||1),1);
 
 const columnGroups=[{name:'Arus jurusan',codes:params.filter(p=>p.code.startsWith('I_')).map(p=>p.code)},
  {name:'Tegangan rel',codes:params.filter(p=>p.code.startsWith('V_')&&!p.code.startsWith('V_END')).map(p=>p.code)},
  {name:'Tegangan ujung',codes:params.filter(p=>p.code.startsWith('V_END')).map(p=>p.code)},
  {name:'Grounding',codes:params.filter(p=>p.code.startsWith('GROUND')).map(p=>p.code)}];
 const cols=useMemo(()=>orderColumns(columnsFromParams(params,codesForGroups(columnGroups,chosenGroups)),maxLine),[defs.params,chosenGroups,maxLine]);
 const plan=useMemo(()=>headerPlan(cols),[cols]);
 const paramById=useMemo(()=>new Map(params.map(p=>[p.id,p.code])),[defs.params]);
 const persist=()=>pendingRecovery.current&&!Object.keys(draftsRef.current).length
   ?true:saveBackup(storage(),key,draftsRef.current,{});
 const setDraft=(next:Record<string,string>)=>{draftsRef.current=next;setDrafts(next)};
 const setVisit=(item:Visit)=>{visitsRef.current={...visitsRef.current,[item.substation_id]:item};setVisits(visitsRef.current)};
 const savedRaw=(id:number,column:GridColumn)=>{
  const visit=visitsRef.current[id];if(!visit)return '';
  const value=visit.values?.find(v=>paramById.get(v.param_id)===column.code&&v.line_no===column.line);
  return value?.flag?'@'+value.flag:value?.value==null?'':String(value.value);
 };
 const raw=(row:Substation,column:GridColumn)=>{
  const k=cellKey(row.id,column.code,column.line);
  return draftsRef.current[k]??savedRaw(row.id,column);
 };
 async function sendRow(id:number){
  const changed=Object.entries(draftsRef.current).filter(([key])=>key.startsWith(id+'|'));
  if(!changed.length)return;
  const values=changed.map(([key,text])=>{
   const [,code,line]=key.split('|');
   return {code,line_no:Number(line),value:text.startsWith('@')?null:parseNumber(text),
    flag:text.startsWith('@')?text.slice(1):null};
  });
  const current=visitsRef.current[id];
  const response=await apiFetch('/api/substations/measurements',{method:'PUT',body:JSON.stringify({
   substation_id:id,measured_on:day,session,revision:current?.revision??null,
   technician,values
  })});
  if(!response.ok){const detail=await apiError(response);
   if(response.status===409&&typeof detail==='object'&&detail.server){
    setConflict(v=>({...v,[id]:detail.server}));
   }else if(response.status===401)setExpired(true);
   else setMessage(typeof detail==='string'?detail:JSON.stringify(detail));
   throw {status:response.status};
  }
  const result=await response.json();
  const next={...draftsRef.current};
  for(const [k,text] of changed)if(next[k]===text)delete next[k];
  setDraft(next);setVisit(result.measurement);persist();
  if(selectedCalc?.id===result.measurement.id)setSelectedCalc({id:result.measurement.id,data:result.calculated});
 }
 const queue=useMemo(()=>new HourQueue(sendRow,(id,status)=>setStatuses(old=>({...old,
   [id]:status==='tersimpan'?`tersimpan ${new Date().toLocaleTimeString('id-ID')}`:status
 })),3000),[day,session,unitId,user.id]);
 useEffect(()=>()=>{queue.stop();persist()},[queue]);
 useEffect(()=>{const timer=setTimeout(persist,500);setDirty(Object.keys(drafts).length>0);
  return()=>clearTimeout(timer)},[drafts,key]);
 useEffect(()=>{const close=(event:BeforeUnloadEvent)=>{if(Object.keys(draftsRef.current).length){
   persist();event.preventDefault();event.returnValue='';}};
  const other=(event:StorageEvent)=>{if(event.key===key)setOtherTab(true)};
  window.addEventListener('beforeunload',close);window.addEventListener('storage',other);
  return()=>{window.removeEventListener('beforeunload',close);window.removeEventListener('storage',other);setDirty(false)};
 },[key]);
 async function reload(){setBusy(true);setMessage('');
  try{const search=new URLSearchParams({page:String(page),page_size:'100',active:'true'});
   if(feeder)search.set('feeder_id',feeder);
   const data=await api<Page<Substation>>('/substations/master?'+search);
   const selected=data.items;   // 9d-4: an ULP also fills its KPs' gardu (server restricts the list)
   setRows(selected);setTotal(data.total);
   const v=selected.length?await api<{items:Visit[]}>(`/substations/measurements/grid?day=${day}&session=${session}&ids=${selected.map(m=>m.id).join(',')}`):{items:[]};
   visitsRef.current=Object.fromEntries(v.items.map(x=>[x.substation_id,x]));setVisits(visitsRef.current);setSelectedCalc(null);
   const b=readBackup(storage(),key);pendingRecovery.current=!!(b&&Object.keys(b.drafts).length);
   setDraft({});setStatuses({});setConflict({});setPicked([]);setBackup(pendingRecovery.current?b:null);
  }catch(e){setMessage(msg(e))}finally{setBusy(false)}
 }
 useEffect(()=>{void reload()},[day,session,page,feeder,unitId]);
 const edit=(id:number,column:GridColumn,text:string)=>{if(readonly||visitsRef.current[id]?.state==='verified')return;
  pendingRecovery.current=false;setDraft({...draftsRef.current,[cellKey(id,column.code,column.line)]:text});queue.mark(id);
 };
 const patch=(changes:Record<string,string>)=>{pendingRecovery.current=false;setLastEdit({...draftsRef.current});
  setDraft({...draftsRef.current,...changes});
  Object.keys(changes).forEach(key=>queue.mark(Number(key.split('|')[0])));
 };
 const paste=(event:React.ClipboardEvent<HTMLInputElement>,ri:number,ci:number)=>{
  const text=event.clipboardData.getData('text');if(!/[\t\n]/.test(text))return;
  event.preventDefault();const parsed=parsePaste(text,ri,ci,rows,cols,allowedCell);
  patch(parsed.changes);if(parsed.omitted)setMessage(`${parsed.omitted} sel di luar kisi/jurusan diabaikan`);
 };
 const handleKey=(event:React.KeyboardEvent<HTMLInputElement>,ri:number,ci:number)=>{
  const next=nextCell(ri,ci,event.key,rows.length,cols.length);if(!next)return;
  event.preventDefault();const [r,c]=next;
  document.querySelector<HTMLInputElement>(`[data-gridcell="${r}:${c}"]`)?.focus();
 };
 const resolve=(id:number,useServer:boolean)=>{
  const server=conflict[id];if(!server)return;
  const next={...draftsRef.current};
  if(useServer){
   const copy=Object.fromEntries(Object.entries(next).filter(([k])=>k.startsWith(id+'|')));
   const previous=readBackup(storage(),key+':conflict');
   const combined={...(previous?.drafts||{}),...(conflictCopy||{}),...copy};
   setConflictCopy(combined);
   saveBackup(storage(),key+':conflict',combined,{});
   for(const k of Object.keys(copy))delete next[k];
  }
  pendingRecovery.current=false;setDraft(next);setVisit(server);
  setConflict(old=>{const result={...old};delete result[id];return result});
  if(!useServer)void queue.resolve(id);
 };
 async function loginAgain(){try{const r=await apiFetch('/api/auth/login',{
  method:'POST',body:JSON.stringify(login)});if(!r.ok)throw new Error('Login gagal');
  const response=await r.json();if(response.user.id!==user.id)throw new Error('Akun berbeda: cadangan tidak dikirim');
  setCSRF(response.csrf);setExpired(false);await queue.resume();setMessage('Sesi dilanjutkan');
  }catch(e){setMessage(msg(e))}}
 const editable=!readonly && unitId>0;

 const states=rows.map(r=>rowState({verified:visits[r.id]?.state==='verified',conflict:!!conflict[r.id],queue:statuses[r.id],filled:!!visits[r.id]?.values?.length}));
 const sum=summarizeRows(states);
 const targets=picked.length?rows.filter(r=>picked.includes(r.id)):rows;
 function fillFromFocus(){if(!focusCell)return setMessage('Klik dulu sel sumber, lalu pilih baris tujuan.');
  const [ri,ci]=focusCell,col=cols[ci],src=rows[ri];if(!col||!src)return;
  const text=raw(src,col),changes:Record<string,string>={};
  for(const r of (picked.length?targets:rows.slice(ri+1)))if(r.id!==src.id&&allowedCell(r,col)&&visits[r.id]?.state!=='verified')changes[cellKey(r.id,col.code,col.line)]=text;
  patch(changes);}
 function markFlag(){if(!focusCell)return setMessage('Klik dulu sel yang akan ditandai.');
  const flag=defs.flags.find(f=>f.active);const [ri,ci]=focusCell;if(!flag||!rows[ri]||!cols[ci])return;edit(rows[ri].id,cols[ci],'@'+flag.code);}
 async function verifyPicked(){const ids=targets.map(r=>visits[r.id]?.id).filter((x):x is number=>!!x);
  if(!ids.length)return setMessage('Baris terpilih belum punya pengukuran tersimpan.');
  try{await queue.flushAll();const res=await api<{results:{id:number;status:string;reason?:string}[]}>('/substations/measurements/actions',{method:'POST',body:JSON.stringify({ids,action:'verify',reason:'',changes:{}})});
   const bad=res.results.filter(x=>x.status==='error');setMessage(bad.length?`${ids.length-bad.length} terverifikasi, ${bad.length} gagal: ${bad[0].reason}`:`${ids.length} pengukuran terverifikasi`);await reload();}
  catch(e){setMessage(msg(e))}}
 const canVerify=user.role==='admin'||user.role==='verifier';
 return <div className="substation-stack gx-page">
  <div className="gx-head"><div><span className="substation-kicker">PENGUKURAN GARDU · INPUT MASSAL</span><h3>Input Pengukuran</h3><p>Ketik atau tempel langsung dari Excel · tersimpan otomatis per baris · data terverifikasi terkunci.</p></div>
   <div className="an-actions"><button className="btn secondary" onClick={()=>void downloadApi('/substations/measurements/template?'+new URLSearchParams({day,session,...(feeder?{feeder_id:feeder}:{})}),'pengukuran_gardu.xlsx').catch(e=>setMessage(msg(e)))}>Unduh template Excel</button>
    {editable&&onNavigate&&<button className="btn secondary" onClick={()=>onNavigate('visits')}>Unggah Excel</button>}
    <button className="btn primary" disabled={!editable||!Object.keys(drafts).length} onClick={()=>void queue.flushAll()}>Simpan semua</button></div></div>
  <div className="gx-filters">
   <label>Tanggal ukur<input type="date" value={day} onChange={e=>{setDay(e.target.value);setPage(1)}}/></label>
   <label>Sesi<select value={session} onChange={e=>setSession(e.target.value)}>{defs.sessions.filter(s=>s.active).map(s=><option key={s.code} value={s.code}>{s.name}</option>)}</select></label>
   <label>Penyulang<select value={feeder} onChange={e=>{setFeeder(e.target.value);setPage(1)}}><option value="">Semua ({total} gardu)</option>{feeders.filter(f=>f.active).map(f=><option key={f.id} value={f.id}>{f.name}</option>)}</select></label>
   <label className="gx-tech">Petugas<input value={technician} disabled={!editable} onChange={e=>setTechnician(e.target.value)} placeholder="Regu · nama petugas"/></label>
   <div className="gx-chips" role="group" aria-label="Kolom tampil"><span>Kolom tampil:</span>
    {columnGroups.filter(g=>g.codes.length).map(g=>{const on=!chosenGroups.length||chosenGroups.includes(g.name);
     return <button key={g.name} aria-pressed={on} className={'gx-chip'+(on?' on':'')} onClick={()=>setChosenGroups(cur=>{const base=cur.length?cur:columnGroups.filter(x=>x.codes.length).map(x=>x.name);
      const next=base.includes(g.name)?base.filter(x=>x!==g.name):[...base,g.name];return next.length===columnGroups.filter(x=>x.codes.length).length?[]:next.length?next:cur;})}>{g.name}</button>})}</div>
  </div>
  <div className="gx-bar"><strong>{picked.length?`${picked.length} baris dipilih`:'Semua baris'}</strong>
   <button className="btn secondary sm" disabled={!editable} onClick={fillFromFocus} title="Salin sel yang terakhir diklik ke baris terpilih (atau semua baris di bawahnya)">Isi ke bawah</button>
   <button className="btn secondary sm" disabled={!editable} onClick={markFlag}>Tandai {defs.flags.find(f=>f.active)?.name??'PUTUS'}</button>
   {canVerify&&<button className="btn secondary sm" disabled={!editable} onClick={()=>void verifyPicked()}>Verifikasi</button>}
   <button className="btn secondary sm" disabled={!lastEdit} onClick={()=>{if(lastEdit){setDraft(lastEdit);setLastEdit(null)}}}>Urungkan</button>
   <span className="gx-sum">{sum.saved} tersimpan · {sum.saving} menunggu · {sum.conflict} konflik · {sum.empty} belum diisi{Object.keys(drafts).length?' · cadangan lokal aktif':''}</span></div>
  {message&&<div className="notice info" role="status">{message}</div>}{readonly&&<div className="notice info">Hanya lihat — pengukuran tidak dapat diubah.</div>}
  {otherTab&&<div className="notice info">Hari yang sama dibuka di tab lain. Tidak ada sinkronisasi otomatis.</div>}
  {backup&&<div className="notice warning">Ada isian belum tersimpan dari {new Date(backup.changedAt).toLocaleString('id-ID')}.
    <button className="btn sm primary" onClick={()=>{pendingRecovery.current=false;setDraft(backup.drafts);Object.keys(backup.drafts).forEach(k=>queue.mark(Number(k.split('|')[0])));setBackup(null)}}>Pulihkan</button>
    <button className="btn sm secondary" onClick={()=>{pendingRecovery.current=false;saveBackup(storage(),key,{},{});setBackup(null)}}>Buang</button></div>}
  {expired&&<div className="substation-dialog"><h3>Sesi berakhir, masuk kembali</h3><input placeholder="Username" value={login.username} onChange={e=>setLogin(v=>({...v,username:e.target.value}))}/><input type="password" value={login.password} onChange={e=>setLogin(v=>({...v,password:e.target.value}))}/><button className="btn primary" onClick={loginAgain}>Masuk dan lanjutkan</button></div>}
  {conflictCopy&&<div className="notice warning">Ketikan dari konflik tetap disimpan sebagai cadangan.
   <button className="btn secondary sm" onClick={()=>{patch(conflictCopy);setConflictCopy(null)}}>Kembalikan ketikan</button>
   <button className="btn secondary sm" onClick={()=>setConflictCopy(null)}>Tutup</button></div>}
  <GridTable rows={rows} cols={cols} plan={plan} visits={visits} statuses={statuses} conflicts={conflict} picked={picked} editable={editable} flags={defs.flags}
   raw={raw} onPick={setPicked} onEdit={edit} onFlush={id=>void queue.flush(id)} onPaste={paste} onKey={handleKey} onFocusCell={(r,c)=>setFocusCell([r,c])}
   onResult={v=>api<CalcResults>(`/substations/calculations/measurements/${v.id}/results`).then(data=>setSelectedCalc({id:v.id,data})).catch(e=>setMessage(msg(e)))}
   onConflict={id=>document.getElementById('gx-conflict-'+id)?.scrollIntoView({behavior:'smooth'})}/>
  {!rows.length&&<div className="gx-empty"><b>{busy?'Memuat gardu…':'Belum ada gardu aktif di unit ini'}</b>{!busy&&<span>Tambahkan gardu di menu Master, lalu kembali ke sini.</span>}</div>}
  <div className="gx-pager"><span>{total} gardu · halaman {page}</span><button className="btn secondary sm" disabled={page<=1} onClick={()=>setPage(page-1)}>‹ Sebelumnya</button><button className="btn secondary sm" disabled={page*100>=total} onClick={()=>setPage(page+1)}>Berikutnya ›</button></div>
  {selectedCalc&&<div className="calc-card"><button className="btn secondary sm" onClick={()=>setSelectedCalc(null)}>Tutup hasil</button><ResultPanel data={selectedCalc.data}/></div>}
  <div className="gx-help">
   <section><h4>Cara cepat</h4><p>Panah dan Enter untuk pindah sel · tempel blok dari Excel (koma desimal diterima) · klik sel lalu “Isi ke bawah” · Urungkan membatalkan ubahan terakhir.</p></section>
   <section><h4>Arti tampilan sel</h4><p>Arsir = jurusan tidak ada di gardu itu · kosong = belum diukur (bukan nol) · label ungu = penanda seperti PUTUS, bukan angka.</p></section>
   {Object.entries(conflict).map(([id,server])=><section key={id} id={'gx-conflict-'+id} className="gx-conflict"><ConflictDialog id={Number(id)} server={server}
    drafts={drafts} params={params} onReload={()=>resolve(Number(id),true)} onKeep={()=>resolve(Number(id),false)}/></section>)}
  </div>
 </div>;
}
