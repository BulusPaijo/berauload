import {useEffect,useState} from 'react';
import type {ReactNode} from 'react';
import {AlertCircle,CheckCircle2,RefreshCw,Save,ShieldCheck} from 'lucide-react';
import {api,unitCacheKey,isoWita,num,qs} from '../../api';
import type {Catalog,DayData,User} from '../../api';
import type {InputFormConfig} from './types';
import {DEFAULT_TABS} from './types';
import './input-form.css';
import {useHourlyAutosave} from './autosave/useHourlyAutosave';
import InputSaveFeedback from './autosave/InputSaveFeedback';

const messageOf=(e:unknown)=>e instanceof Error?e.message:String(e);
function Notice({children,type}:{children:ReactNode,type:'error'|'success'}){
 return <div className={'notice '+type} role={type==='error'?'alert':'status'}><AlertCircle size={17}/>{children}</div>;
}
function Loading(){return <div className="loading">Memuat data...</div>}

export default function InputPage({catalog,user,unitLevel}:{catalog:Catalog,user:User,unitLevel:'up3'|'ulp'|'kp'}){
 const [day,setDay]=useState(sessionStorage.getItem(unitCacheKey('berauload_day'))||isoWita());
 const [group,setGroup]=useState('PEMBANGKIT'),[data,setData]=useState<DayData|null>(null);
 const [busy,setBusy]=useState(false),[saving,setSaving]=useState(false),[notice,setNotice]=useState(''),[error,setError]=useState('');
 const canEdit=['admin','operator','verifier'].includes(user.role)&&unitLevel!=='up3'&&data?.status==='draft';
 const auto=useHourlyAutosave(day,user,canEdit,(hour,values,computed)=>{
  setData(old=>old?{...old,hours:old.hours.map(row=>{
    if(row.hour!==hour)return row;
    const merged={...row.values};
    for(const [code,value] of Object.entries({...values,...computed})){
      if(value===null)delete merged[code];else merged[code]=value;
    }
    return {...row,values:merged};
  })}:old);
 });
 const {drafts,dirtyHours}=auto;
 const [layout,setLayout]=useState<InputFormConfig|null>(null);
 const [layoutError,setLayoutError]=useState('');
 const [actors,setActors]=useState<{status:string;verified_by?:{name:string;admin_global:boolean}|null;finalized_by?:{name:string;admin_global:boolean}|null;draft_kps?:{id:number;name:string}[];source_changed_after_final?:boolean;changed_sources?:number[]}|null>(null);
 const [treeResult,setTreeResult]=useState<{unit_code:string;result:string;reason:string|null;status:string}[]|null>(null);
 useEffect(()=>{let ok=true;
  api<InputFormConfig>('/input-form/config').then(v=>{if(ok){setLayout(v);setLayoutError('');}})
    .catch(e=>{if(ok)setLayoutError(messageOf(e));});
  return()=>{ok=false};
 },[catalog]);
 const tabs=(layout?.tabs||DEFAULT_TABS).filter(t=>t.active).sort((a,b)=>a.display_order-b.display_order);
 const placementByCode=new Map((layout?.placements||[]).map(p=>[p.metric_code,p]));
 useEffect(()=>{if(tabs.length&&!tabs.some(t=>t.code===group))setGroup(tabs[0].code);},[layout,group]);
 const metrics=catalog.metrics.filter(m=>{
  const position=placementByCode.get(m.code);
  const tab=position?.tab_code||m.group;
  return m.active&&tab===group&&(position?.visible??m.code!=='daya_mampu_sistem_kw');
 }).sort((a,b)=>(placementByCode.get(a.code)?.display_order??a.id)-(placementByCode.get(b.code)?.display_order??b.id));
 function refresh(){setBusy(true);setError('');api<any>(`/days/${day}/status`).then(setActors).catch(()=>setActors(null));api<DayData>(`/records/day?${qs({day})}`).then(r=>{setData(r);auto.loaded(r)}).catch(e=>setError(messageOf(e))).finally(()=>setBusy(false))}
 useEffect(()=>{sessionStorage.setItem(unitCacheKey('berauload_day'),day);refresh()},[day]);
 async function saveAll(){if(!dirtyHours.length)return;setSaving(true);setError('');
  try{await auto.saveAll();setNotice('Permintaan simpan semua telah diproses. Periksa status tiap jam.');}
  catch(e){setError(messageOf(e))}finally{setSaving(false)}
 }
 async function statusAction(action:'verify'|'finalize'|'reopen'){
  if(dirtyHours.length){auto.persist();setError('Simpan dahulu seluruh perubahan sebelum mengubah status hari.');return;}
  const label=action==='verify'?'verifikasi':action==='finalize'?'finalisasi':'pembukaan ulang';
  const reason=window.prompt(`Catatan/alasan ${label} (wajib):`,'Data telah diperiksa');
  if(!reason||reason.trim().length<3)return;
  const pending=action==='finalize'?(actors?.draft_kps||[]):[];
  const confirm_draft_sources=pending.length>0&&window.confirm(`KP masih draf: ${pending.map(u=>u.name).join(', ')}. Tetap finalkan ULP?`);
  if(pending.length>0&&!confirm_draft_sources)return;
  setSaving(true);
  try{await api(`/days/${day}/${action}`,{method:'POST',body:JSON.stringify({reason:reason.trim(),confirm_draft_sources})});setNotice(`Status berhasil diperbarui: ${label}.`);refresh();}catch(e){setError(messageOf(e))}finally{setSaving(false)}
 }
 async function treeAction(action:'verify'|'finalize'){
  if(dirtyHours.length){auto.persist();setError('Simpan dahulu perubahan sebelum tindakan massal.');return;}
  setTreeResult(null);setError('');
  try{const preview=await api<{units:{unit_code:string;result:string;reason:string|null;status:string}[]}>(`/days/${day}/tree-preview?action=${action}`);
   setTreeResult(preview.units);
   const summary=preview.units.map(u=>`${u.unit_code}: ${u.result}${u.reason?' ('+u.reason+')':''}`).join('\n');
   if(!preview.units.some(u=>u.result==='diproses'))return;
   if(!window.confirm(`Pratinjau ${action}:\n${summary}\n\nLanjutkan?`))return;
   const reason=window.prompt('Alasan tindakan massal (minimal 3 karakter):','Data telah diperiksa');
   if(!reason||reason.trim().length<3)return;
   setSaving(true);
   const pending=action==='finalize'?(actors?.draft_kps||[]):[];
   const confirm_draft_sources=pending.length>0&&window.confirm(`KP masih draf: ${pending.map(u=>u.name).join(', ')}. Tetap finalkan ULP?`);
   if(pending.length>0&&!confirm_draft_sources)return;
   const result=await api<{units:typeof preview.units}>(`/days/${day}/${action}-tree`,{method:'POST',body:JSON.stringify({reason:reason.trim(),confirm_draft_sources})});
   setTreeResult(result.units);refresh();
  }catch(e){setError(messageOf(e))}finally{setSaving(false)}
 }
 return <div className="page-space"><div className="page-top"><div><div className="eyebrow">FORMULIR OPERASIONAL</div><h2>Input Beban Harian</h2><p>Pencatatan per jam menggunakan format parameter laporan Berau.</p></div><div className="period-input"><input type="date" value={day} onChange={e=>setDay(e.target.value)}/></div></div>{error&&<Notice type="error">{error}</Notice>}{layoutError&&<Notice type="error">Pengaturan tab gagal dimuat: {layoutError}. Tampilan standar digunakan.</Notice>}{notice&&<Notice type="success">{notice}</Notice>}
 <div className="panel"><div className="entry-toolbar"><div className="status-line"><span className={'tag '+(data?.status==='final'?'success':data?.status==='verified'?'info':'warning')}>{data?.status==='final'?'Final':data?.status==='verified'?'Terverifikasi':'Draft'}</span><span className="muted">{data?.filled_hours||0} dari 24 jam memiliki data</span><span className="muted small">Autosave: {dirtyHours.length} jam belum tersimpan</span></div><div className="toolbar-actions"><button className="btn secondary sm" onClick={()=>{if(!dirtyHours.length||window.confirm('Ada isian belum tersimpan. Muat ulang data server?'))refresh()}}><RefreshCw size={15}/> Muat Ulang</button>{canEdit&&<button className="btn primary sm" onClick={saveAll} disabled={!dirtyHours.length||saving}><Save size={15}/> Simpan {dirtyHours.length?`${dirtyHours.length} Jam`:''}</button>}</div></div><div className="tabstrip">{tabs.map(t=><button key={t.code} onClick={()=>setGroup(t.code)} className={group===t.code?'active':''}>{t.name}</button>)}</div>{busy?<Loading/>:<div className="entry-scroller"><table className="entry-table"><thead><tr><th className="sticky-hour">Jam</th>{metrics.map(m=><th key={m.code}>{m.name}<small>{m.unit}</small></th>)}</tr></thead><tbody>{Array.from({length:24},(_,h)=><tr key={h}><td className="sticky-hour"><strong>{String(h).padStart(2,'0')}:00</strong><small className="autosave-status">{auto.statuses[h]||''}</small></td>{metrics.map(m=>{const key=`${h}:${m.code}`;const original=data?.hours[h]?.values[m.code];const isEditable=canEdit&&m.mode==='input';const editValue=key in drafts?drafts[key]:original==null?'':String(original);
 return <td key={m.code}>{isEditable?<input className={key in drafts?'edited':''} aria-label={`${m.name} jam ${h}`} type="text" inputMode="decimal" value={editValue} placeholder="—" onChange={e=>auto.edit(h,m.code,e.target.value,original??null)} onBlur={()=>void auto.flush(h)}/>:<span className={'read-val '+(original==null?'muted':'')}>{original==null?'—':num(original,3)}</span>}</td>})}</tr>)}</tbody></table>{metrics.length===0&&<div className="empty">Belum ada parameter yang ditampilkan pada tab ini. Admin dapat mengaturnya melalui Pengaturan → Form Input.</div>}</div>}<div className="entry-bottom"><span><AlertCircle size={15}/> Kosong berbeda dengan nilai 0. Angka negatif dapat dicatat sesuai kondisi teknis.</span><span>{metrics.length} parameter tampil</span></div></div>
 <InputSaveFeedback user={user} {...auto}/>
 {actors?.source_changed_after_final&&<div className="notice error" role="status">Sumber berubah setelah final/verifikasi. Hasil rekap ULP tetap terkunci; minta admin meninjau dan membuka kembali hari bila diperlukan.</div>}
 {actors&&<div className="muted small">{actors.verified_by&&<>Diverifikasi oleh {actors.verified_by.name}{actors.verified_by.admin_global?' (admin UP3)':''}. </>}{actors.finalized_by&&<>Difinalkan oleh {actors.finalized_by.name}{actors.finalized_by.admin_global?' (admin UP3)':''}.</>}</div>}
 {treeResult&&<div className="panel"><h4>Hasil/pratinjau tindakan massal</h4>{treeResult.map(u=><div key={u.unit_code}>{u.unit_code} — {u.result} — {u.reason??u.status}</div>)}</div>}
 <div className="actions-panel"><div><strong>Kontrol kualitas data</strong><p className="muted small">Verifikasi mengunci input. Finalisasi dapat dilakukan setelah verifikasi; pembukaan ulang hanya oleh admin dengan alasan.</p></div><div className="toolbar-actions">{data?.status==='draft'&&['admin','verifier'].includes(user.role)&&<button className="btn secondary" disabled={saving} onClick={()=>statusAction('verify')}><CheckCircle2 size={16}/> Verifikasi</button>}{data?.status==='verified'&&['admin','verifier'].includes(user.role)&&<button className="btn primary" disabled={saving} onClick={()=>statusAction('finalize')}><ShieldCheck size={16}/> Finalisasi</button>}{data?.status!=='draft'&&user.role==='admin'&&<button className="btn secondary" disabled={saving} onClick={()=>statusAction('reopen')}>Buka Kembali</button>}{unitLevel==='ulp'&&['admin','verifier'].includes(user.role)&&<><button className="btn secondary" disabled={saving} onClick={()=>treeAction('verify')}>Verifikasi ULP beserta KP</button><button className="btn secondary" disabled={saving} onClick={()=>treeAction('finalize')}>Finalkan ULP beserta KP</button></>}</div></div>
 </div>
}

