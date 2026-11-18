import {useActionDialog} from '../ActionDialog';
import {useEffect,useRef,useState} from 'react';
import {api} from '../../../api';
import {displayValue,errorMessage,insertToken,originLabel,recalcDecision} from './helpers.mjs';
import type {CalcColumn,CalcRule,CalcConst,CalcData,CalcTest,CalcPreview,Recalc} from './types';
import './formulas.css';
import CategoryOrder from './CategoryOrder';

const fnTokens=['SUM_JURUSAN(i_r)','MAX_JURUSAN(i_r)','MIN_JURUSAN(v_end_rn)',
 'AVG_JURUSAN(i_r)','AVG( , )','MAX( , )','IF( , , )','AND( , )','OR( , )',
 'FLAG(ground_tr, PUTUS)','KOSONG(ground_tr)','ROUND( , )','ABS( )'];
const blankColumn:CalcColumn={id:0,code:'',name:'',unit:'A',decimals:1,expression:'',empty_mode:'batal',
 description:'',display_order:100,active:true,origin:'custom',default_expression:null};
const blankRule:CalcRule={id:0,code:'',name:'',kind:'finding',group_name:'Temuan',
 expression:'',color:'#355c6d',marker:'circle',display_order:100,active:true,origin:'custom',gardu_count:0};
const request=(path:string,method:string,body:object)=>api(path,{method,body:JSON.stringify(body)});
export default function FormulaSettings({admin}:{admin:boolean}){
 const {confirm:askConfirm,prompt:askText,dialog}=useActionDialog();
 const [data,setData]=useState<CalcData|null>(null),[selected,setSelected]=useState<number|null>(null);
 const [draft,setDraft]=useState<CalcColumn|null>(null),[query,setQuery]=useState('');
 const [panel,setPanel]=useState<'formulas'|'constants'|'settings'>('formulas');
 const [rule,setRule]=useState<CalcRule|null>(null),[message,setMessage]=useState('');
 const [check,setCheck]=useState<{valid:boolean;names:string[];dependencies:string[]}|null>(null);
 const [error,setError]=useState(''),[tested,setTested]=useState<CalcTest|null>(null);
 const [impact,setImpact]=useState<CalcPreview|null>(null),[visits,setVisits]=useState<{id:number;substation_id:number}[]>([]);
 const [testVisit,setTestVisit]=useState(0),[progress,setProgress]=useState<Recalc|null>(null);
 const [histories,setHistories]=useState<{changed_at:string;changed_by:number;before:object;after:object}[]>([]);
 const [constant,setConstant]=useState<CalcConst|null>(null),[staleDays,setStaleDays]=useState(180);
 const inputRef=useRef<HTMLTextAreaElement>(null),stopped=useRef(false),running=useRef(false);
 const reload=async()=>{try{const result=await api<CalcData>('/substations/calculations/definitions');
  setData(result);setStaleDays(result.settings?.stale_days??180);
  setProgress(await api<Recalc>('/substations/calculations/recalculate/status'));
  return result;
 }catch(e){setError(errorMessage(e));return null;}};
 useEffect(()=>{void reload();api<{items:{id:number;substation_id:number}[]}>('/substations/measurements?page_size=100')
  .then(result=>{setVisits(result.items);setTestVisit(result.items[0]?.id??0)}).catch(()=>{});
  return()=>{stopped.current=true};},[]);
 useEffect(()=>{if(!data)return;
  const item=data.columns.find(v=>v.id===selected)??data.columns[0];
  if(item&&selected===null){setSelected(item.id);setDraft({...item});}
 },[data,selected]);
 useEffect(()=>{if(!draft?.expression){setCheck(null);setError('');return;}
  let active=true;const timer=setTimeout(()=>{request('/substations/calculations/check','POST',
   {expression:draft.expression,kind:'column'}).then(value=>{if(active){setCheck(value);setError('');}})
   .catch(e=>{if(active){setCheck(null);setError(errorMessage(e));}});},350);
  return()=>{active=false;clearTimeout(timer)};},[draft?.expression]);
 const update=(patch:Partial<CalcColumn>)=>{setDraft(v=>v?{...v,...patch}:v);setImpact(null);setTested(null);};
 const select=(item:CalcColumn)=>{setSelected(item.id);setDraft({...item});setRule(null);
  setHistories([]);setImpact(null);setTested(null);setMessage('');};
 const insert=(token:string)=>{if(!draft||!admin)return;
  const editor=inputRef.current,start=editor?.selectionStart??draft.expression.length,
    end=editor?.selectionEnd??start,edited=insertToken(draft.expression,token,start,end);
  update({expression:edited.value});requestAnimationFrame(()=>{editor?.focus();editor?.setSelectionRange(edited.caret,edited.caret);});};
 const history=async(kind:string,code:string)=>{try{setHistories(await api(`/substations/calculations/history/${kind}/${code}`));}
  catch(e){setMessage(errorMessage(e));}};
 const recalc=async()=>{if(running.current)return;running.current=true;stopped.current=false;try{for(let i=0;i<1000&&!stopped.current;i++){
  const status=await api<Recalc>('/substations/calculations/recalculate?limit=100',{method:'POST'});
  setProgress(status);
  if(recalcDecision(status)==='retry'){setMessage('Hitung ulang sedang dikerjakan pengguna lain, mencoba lagi…');
   await new Promise(resolve=>setTimeout(resolve,2500));continue;}
  if(recalcDecision(status)==='stop')break;
 }setMessage('Status hitung ulang diperbarui. Bisa dilanjutkan bila belum selesai.');}
 catch(e){setMessage(errorMessage(e));}finally{running.current=false;}};
 const saveColumn=async()=>{if(!draft||!admin)return;
  if(!draft.code||!draft.name||!draft.expression){setMessage('Nama, kode, dan rumus wajib diisi.');return;}
  if(error){setMessage('Perbaiki rumus sebelum menyimpan: '+error);return;}
  if(!impact&&draft.id){setMessage('Jalankan pratinjau dampak sebelum menyimpan.');return;}
  if(!(await askConfirm('Simpan definisi global? Semua hasil pengukuran harus dihitung ulang.')))return;
  try{const response=await request('/substations/calculations/'+(draft.id?'column/'+draft.id:'column'),
      draft.id?'PATCH':'POST',draft) as CalcColumn;
   setSelected(response.id);const refreshed=await reload();if(refreshed)setDraft({...response});
   setMessage('Definisi tersimpan. Hitung ulang berjalan bertahap.');setImpact(null);void recalc();
  }catch(e){setMessage(errorMessage(e));}};
 const test=async()=>{if(!draft||!testVisit)return;
  try{setTested(await request('/substations/calculations/test','POST',{
   code:draft.id?draft.code:null,expression:draft.expression,kind:'column',
   empty_mode:draft.empty_mode,measurement_id:testVisit}) as CalcTest);}
  catch(e){setMessage(errorMessage(e));}};
 const preview=async()=>{if(!draft?.id)return setMessage('Buat kolom dahulu untuk pratinjau dampak.');
  try{setImpact(await request('/substations/calculations/preview','POST',{
   code:draft.code,expression:draft.expression,kind:'column',empty_mode:draft.empty_mode,
   limit:100}) as CalcPreview);}
  catch(e){setMessage(errorMessage(e));}};
 const restore=async()=>{if(!draft?.id||!admin||!(await askConfirm('Kembalikan seluruh atribut kolom ke bawaan?')))return;
  try{const item=await api<CalcColumn>(`/substations/calculations/columns/${draft.id}/restore`,{method:'POST'});
   setDraft(item);await reload();setMessage('Rumus bawaan dipulihkan.');void recalc();}
  catch(e){setMessage(errorMessage(e));}};
 const archiveColumn=async()=>{if(!draft?.id||!admin||!(await askConfirm('Arsipkan kolom ini?')))return;
  try{await request(`/substations/calculations/column/${draft.id}`,'PATCH',{active:!draft.active});
   await reload();setDraft(v=>v?{...v,active:!v.active}:v);setMessage('Status kolom diubah.');}
  catch(e){setMessage(errorMessage(e));}};
 const saveRule=async()=>{if(!rule||!admin)return;
  if(!rule.code||!rule.name||!rule.expression)return setMessage('Kode, nama dan syarat wajib diisi.');
  if(!(await askConfirm('Simpan aturan global dan hitung ulang seluruh pengukuran?')))return;
  try{await request(`/substations/calculations/rule${rule.id?'/'+rule.id:''}`,rule.id?'PATCH':'POST',rule);
   await reload();setRule(null);setMessage('Aturan disimpan.');void recalc();}
  catch(e){setMessage(errorMessage(e));}};
 const saveConstant=async()=>{if(!constant||!admin)return;
  if(!(await askConfirm('Simpan konstanta global dan hitung ulang?')))return;
  try{await request(`/substations/calculations/constant${constant.id?'/'+constant.id:''}`,
   constant.id?'PATCH':'POST',constant);await reload();setConstant(null);
   setMessage('Konstanta tersimpan.');void recalc();}
  catch(e){setMessage(errorMessage(e));}};
 const orderRules=async(codes:string[])=>{if(!admin)return;
  try{await request('/substations/calculations/rules/reorder','POST',{kind:'category',codes});
   await reload();setMessage('Urutan kategori diperbarui.');}catch(e){setMessage(errorMessage(e));}};
 const reorder=async(item:CalcColumn,delta:number)=>{if(!admin||!data)return;
  const sorted=data.columns.slice().sort((a,b)=>a.display_order-b.display_order);
  const index=sorted.findIndex(r=>r.id===item.id),other=sorted[index+delta];if(!other)return;
  try{await request(`/substations/calculations/column/${item.id}`,'PATCH',{display_order:other.display_order});
   await request(`/substations/calculations/column/${other.id}`,'PATCH',{display_order:item.display_order});
   await reload();}catch(e){setMessage(errorMessage(e));}};
 const applyDays=async()=>{try{await request('/substations/calculations/settings','POST',{stale_days:staleDays});
  await reload();setMessage('Pengaturan belum diukur telah disimpan.');}catch(e){setMessage(errorMessage(e));}};
 return <div className="calc-page">{dialog}
  <header className="calc-head"><div><div className="substation-kicker">PENGATURAN · GARDU · RUMUS & KATEGORI</div>
   <h2>Rumus & Kategori</h2><p>Berlaku untuk semua unit · {admin?'Admin dapat mengubah':'Hanya lihat'} · setiap perubahan tercatat</p></div>
   <div className="calc-head-actions"><button className="btn secondary" onClick={()=>draft?.code&&history('column',draft.code)}>Riwayat perubahan</button>
    <button className="btn secondary" onClick={()=>setPanel(panel==='constants'?'formulas':'constants')}>Konstanta & pengaturan</button>
    {admin&&<button className="btn secondary" onClick={async()=>{if(!(await askConfirm('Kembalikan semua kolom bawaan? Perubahan kustom tetap tersimpan.')))return;
     try{await api('/substations/calculations/columns/restore-all',{method:'POST'});await reload();
      setMessage('Semua kolom bawaan dipulihkan; hitung ulang diperlukan.');}
      catch(e){setMessage(errorMessage(e))}}}>Kembalikan semua ke bawaan</button>}
    {admin&&<button className="btn primary" onClick={()=>{setDraft({...blankColumn});setSelected(0);setPanel('formulas');setImpact(null)}}>+ Kolom hitung baru</button>}</div></header>
  {data?.warning&&<p className="calc-notice">{data.warning}. Nilai awal bukan keputusan standar teknis yang telah disahkan.</p>}
  {message&&<div role="status" className="notice info">{message}</div>}
  {progress&&<div className="calc-recalc"><span>Versi {progress.version} · {progress.completed} dari {progress.total} pengukuran selesai</span>
   <progress value={progress.completed} max={Math.max(1,progress.total)} />
   {admin&&<><button className="btn secondary sm" onClick={()=>void recalc()} disabled={!progress.remaining}>Hitung ulang / lanjutkan</button>
    <button className="btn secondary sm" onClick={()=>{stopped.current=true}}>Hentikan setelah batch</button></>}</div>}
  {panel==='constants'&&<section className="calc-card calc-config"><h3>Konstanta bernama</h3><p>Konstanta berlaku global dan digunakan oleh rumus aktif.</p>
   <div className="calc-constant-list">{data?.constants.map(item=><button key={item.id} className="calc-line" onClick={()=>setConstant({...item})}>
    <b>{item.code}</b> {displayValue(item.value,3)} {item.unit}</button>)}</div>
   {admin&&<button className="btn secondary" onClick={()=>setConstant({id:0,code:'',name:'',value:0,unit:'—',description:'',active:true})}>+ Konstanta</button>}
   {constant&&<div className="calc-form-grid"><label>Kode<input disabled={!!constant.id||!admin} value={constant.code} onChange={e=>setConstant({...constant,code:e.target.value})}/></label>
    <label>Nama<input disabled={!admin} value={constant.name} onChange={e=>setConstant({...constant,name:e.target.value})}/></label>
    <label>Nilai<input disabled={!admin} type="number" value={constant.value} onChange={e=>setConstant({...constant,value:Number(e.target.value)})}/></label>
    <label>Satuan<input disabled={!admin} value={constant.unit} onChange={e=>setConstant({...constant,unit:e.target.value})}/></label>
    {admin&&<button className="btn primary" onClick={saveConstant}>Simpan konstanta</button>}</div>}
   <h3>Belum diukur</h3><label>Jumlah hari <input type="number" min={1} max={3650} disabled={!admin} value={staleDays} onChange={e=>setStaleDays(Number(e.target.value))}/></label>
   {admin&&<button className="btn secondary" onClick={applyDays}>Simpan pengaturan</button>}
   <button className="btn secondary" onClick={()=>setPanel('formulas')}>Kembali ke rumus</button></section>}
  {panel==='formulas'&&<div className="calc-layout">
   <aside className="calc-card calc-list"><h3>Kolom hitung ({data?.columns.filter(c=>c.active).length??0})</h3>
    <input placeholder="Cari kolom atau kode" value={query} onChange={e=>setQuery(e.target.value)}/>
    <div className="calc-list-items">{data?.columns.filter(item=>(item.name+' '+item.code).toLowerCase().includes(query.toLowerCase()))
     .map(item=><div key={item.id} className={'calc-list-item '+(draft?.id===item.id?'active':'')}>
       <button onClick={()=>select(item)}><strong>{item.name}</strong><small>{item.code}</small></button>
       <span className={'calc-badge '+originLabel(item).toLowerCase()}>{originLabel(item)}</span>
       {admin&&<span className="calc-reorder"><button title="Naik" onClick={()=>reorder(item,-1)}>↑</button><button title="Turun" onClick={()=>reorder(item,1)}>↓</button></span>}
       {!item.active&&<span className="calc-warning">Arsip</span>}
      </div>)}</div></aside>
   <section className="calc-card calc-editor">{draft?<>
    <div className="calc-form-grid"><label>Nama kolom<input disabled={!admin} value={draft.name} onChange={e=>update({name:e.target.value})}/></label>
     <label>Kode (permanen)<input disabled={!admin||!!draft.id} value={draft.code} onChange={e=>update({code:e.target.value})}/></label>
     <label>Satuan<input disabled={!admin} value={draft.unit} onChange={e=>update({unit:e.target.value})}/></label>
     <label>Desimal<input type="number" min={0} max={5} disabled={!admin} value={draft.decimals} onChange={e=>update({decimals:Number(e.target.value)})}/></label>
     <label>Saat kosong<select value={draft.empty_mode} disabled={!admin} onChange={e=>update({empty_mode:e.target.value as 'batal'|'lewati'})}><option value="batal">Batal (NULL)</option><option value="lewati">Lewati sel kosong di agregat</option></select></label></div>
    <label className="calc-formula-label">Rumus<textarea spellCheck={false} ref={inputRef} readOnly={!admin} value={draft.expression}
      onChange={e=>update({expression:e.target.value})}/></label>
    <div className="calc-validation" role="status">{error?<span className="calc-error">✕ {error}</span>:
     check?<span className="calc-valid">✓ Rumus sah · memakai {check.names.join(', ')}</span>:<span>Masukkan rumus untuk memeriksa.</span>}</div>
    <h4>Data trafo & konstanta</h4><div className="calc-token-row">{['kva','fase','jumlah_jurusan',...(data?.constants.filter(c=>c.active).map(c=>c.code)??[])].map(token=><button key={token} onClick={()=>insert(token)} disabled={!admin}>{token}</button>)}</div>
    <h4>Parameter ukur & kolom lain</h4><div className="calc-token-row">{['i_r_j1','i_s_j1','i_t_j1','v_r0','ground_tr',...(data?.columns.filter(c=>c.code!==draft.code&&c.active).slice(0,15).map(c=>c.code)??[])].map(token=><button key={token} onClick={()=>insert(token)} disabled={!admin}>{token}</button>)}</div>
    <h4>Fungsi</h4><div className="calc-token-row">{fnTokens.map(token=><button key={token} onClick={()=>insert(token)} disabled={!admin}>{token}</button>)}</div>
    <label className="calc-formula-label">Keterangan<textarea readOnly={!admin} value={draft.description??''} onChange={e=>update({description:e.target.value})}/></label>
    {draft.origin==='default'&&draft.default_expression!==draft.expression&&<div className="calc-notice">Berbeda dari bawaan. <button className="link-btn" onClick={restore} disabled={!admin}>Kembalikan ke bawaan</button></div>}
    <div className="calc-test"><h4>Uji pada gardu contoh</h4><label>Pengukuran<select value={testVisit} onChange={e=>setTestVisit(Number(e.target.value))}><option value={0}>Pilih pengukuran</option>{visits.map(v=><option key={v.id} value={v.id}>Gardu #{v.substation_id} · ukur #{v.id}</option>)}</select></label>
      <button className="btn secondary sm" disabled={!testVisit||!!error} onClick={test}>Jalankan uji</button>
      {tested&&<div className="calc-comparison"><span>Sekarang: <b>{displayValue(tested.current)}</b></span><span>Draf: <b>{displayValue(tested.draft)}</b></span><span>Selisih: <b>{displayValue(tested.difference)}</b></span>
       {!!tested.missing.length&&<small>Kosong: {tested.missing.join(', ')}</small>}</div>}</div>
    <div className="calc-impact"><h4>Dampak bila disimpan</h4><button className="btn secondary sm" disabled={!admin||!draft.id||!!error} onClick={preview}>Pratinjau dampak</button>
      {impact&&<div><p>{impact.scanned} gardu terakhir diperiksa {impact.truncated?'(TERPOTONG)':'· tanpa mengubah data'}</p>
       {Object.entries(impact.rule_changes).map(([key,v])=><div key={key}>{key}: +{v.added} / −{v.removed}</div>)}
       {!Object.keys(impact.rule_changes).length&&<small>Tidak ada perubahan kategori/temuan pada sampel.</small>}</div>}</div>
    {admin&&<div className="calc-actions"><button className="btn primary" onClick={saveColumn}>Simpan & hitung ulang</button>
       {draft.id>0&&<button className="btn secondary" onClick={archiveColumn}>{draft.active?'Arsipkan':'Aktifkan'}</button>}
       <button className="btn secondary" onClick={()=>{const selected=data?.columns.find(c=>c.id===draft.id);if(selected)select(selected)}}>Batal</button></div>}
   </>:<p>Pilih kolom hitung dari daftar.</p>}</section>
   <aside className="calc-right"><section className="calc-card"><div className="calc-side-head"><h3>Kategori pembebanan</h3>{admin&&<button className="btn secondary sm" onClick={()=>setRule({...blankRule,kind:'category',group_name:'Pembebanan'})}>+ Kategori</button>}</div>
      <p>Dicek berurutan dari nomor 1; yang pertama cocok dipakai.{admin&&' Seret ⋮⋮ atau pakai ↑↓ untuk mengubah urutan.'}</p><CategoryOrder rules={data?.rules.filter(r=>r.kind==='category')??[]} admin={admin} active={rule?.id??null} onPick={item=>{setRule({...item});setHistories([])}} onOrder={orderRules}/></section>
    <section className="calc-card"><div className="calc-side-head"><h3>Temuan</h3>{admin&&<button className="btn secondary sm" onClick={()=>setRule({...blankRule})}>+ Temuan</button>}</div>
     <p>Satu gardu dapat memiliki beberapa temuan sekaligus.</p>{data?.rules.filter(r=>r.kind==='finding').map(item=><div className="calc-rule" key={item.id}>
      <button onClick={()=>{setRule({...item});setHistories([])}}><i style={{background:item.color}}/><strong>{item.name}</strong><code>{item.expression}</code><small>{item.gardu_count} gardu</small></button></div>)}</section>
    {rule&&<section className="calc-card calc-rule-editor"><h3>Edit {rule.kind==='category'?'Kategori':'Temuan'}</h3>
      <label>Kode<input disabled={!admin||!!rule.id} value={rule.code} onChange={e=>setRule({...rule,code:e.target.value})}/></label>
      <label>Nama<input disabled={!admin} value={rule.name} onChange={e=>setRule({...rule,name:e.target.value})}/></label>
      <label>Kelompok<input disabled={!admin} value={rule.group_name} onChange={e=>setRule({...rule,group_name:e.target.value})}/></label>
      <label>Syarat<textarea disabled={!admin} value={rule.expression} onChange={e=>setRule({...rule,expression:e.target.value})}/></label>
      <label>Warna<input type="color" disabled={!admin} value={rule.color} onChange={e=>setRule({...rule,color:e.target.value})}/></label>
      <label>Tanda<select value={rule.marker} disabled={!admin} onChange={e=>setRule({...rule,marker:e.target.value})}>{['circle','square','diamond','triangle','exclamation'].map(v=><option key={v}>{v}</option>)}</select></label>
      <label>Urutan<input type="number" disabled={!admin} value={rule.display_order} onChange={e=>setRule({...rule,display_order:Number(e.target.value)})}/></label>
      {admin&&<button className="btn primary" onClick={saveRule}>Simpan aturan</button>}
      {admin&&!!rule.id&&<button className="btn secondary" onClick={async()=>{if(!(await askConfirm('Ubah status aturan?')))return;
       try{await request(`/substations/calculations/rule/${rule.id}`,'PATCH',{active:!rule.active});await reload();setRule(null)}catch(e){setMessage(errorMessage(e))}}}>{rule.active?'Arsipkan':'Aktifkan'}</button>}
      <button className="btn secondary" onClick={()=>rule.code&&void history('rule',rule.code)}>Riwayat</button></section>}
   </aside>
  </div>}
  {!!histories.length&&<section className="calc-card calc-history"><h3>Riwayat perubahan</h3>{histories.map((r,i)=><details key={i}><summary>{r.changed_at} · Pengguna #{r.changed_by}</summary><pre>Sebelum: {JSON.stringify(r.before,null,2)}</pre><pre>Sesudah: {JSON.stringify(r.after,null,2)}</pre></details>)}</section>}
 </div>;
}
