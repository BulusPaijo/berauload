import {useEffect,useMemo,useState} from 'react';
import {ArrowDown,ArrowUp,Eye,EyeOff,Plus,RotateCcw,Save} from 'lucide-react';
import {api} from '../../api';
import type {Catalog} from '../../api';
import type {FormPlacement,FormTab,InputFormConfig} from './types';
import './input-form.css';

const errorText=(e:unknown)=>e instanceof Error?e.message:String(e);
const sorted=(list:FormTab[])=>[...list].sort((a,b)=>a.display_order-b.display_order);
const clone=(x:InputFormConfig)=>JSON.parse(JSON.stringify(x)) as InputFormConfig;

function move<T>(data:T[], index:number, direction:number){
 const other=index+direction;
 if(other<0||other>=data.length)return data;
 const next=[...data];[next[index],next[other]]=[next[other],next[index]];
 return next;
}

export default function InputFormEditor({catalog}:{catalog:Catalog}){
 const [saved,setSaved]=useState<InputFormConfig|null>(null);
 const [draft,setDraft]=useState<InputFormConfig|null>(null);
 const [selected,setSelected]=useState('PEMBANGKIT');
 const [search,setSearch]=useState('');
 const [newTab,setNewTab]=useState('');
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const dirty=Boolean(saved&&draft&&JSON.stringify(saved)!==JSON.stringify(draft));
 const tabs=sorted(draft?.tabs||[]);
 const allRows=useMemo(()=>{
  if(!draft)return [];
  const map=new Map(draft.placements.map(p=>[p.metric_code,p]));
  return catalog.metrics.map(metric=>({metric,placement:map.get(metric.code)}))
    .filter((item):item is {metric:typeof catalog.metrics[number],placement:FormPlacement}=>Boolean(item.placement));
 },[catalog,draft]);
 const entries=allRows.filter(x=>x.placement.tab_code===selected&&
  `${x.metric.name} ${x.metric.code}`.toLowerCase().includes(search.toLowerCase()))
  .sort((a,b)=>a.placement.display_order-b.placement.display_order);

 function load(){
  setBusy(true);setError('');
  api<InputFormConfig>('/input-form/config').then(r=>{
   setSaved(clone(r));setDraft(clone(r));
   setSelected(prev=>r.tabs.some(t=>t.code===prev)?prev:r.tabs[0]?.code||'');
  }).catch(e=>setError(errorText(e))).finally(()=>setBusy(false));
 }
 useEffect(()=>{load()},[]);
 function updateTab(code:string,patch:Partial<FormTab>){
  setDraft(old=>old&&({...old,tabs:old.tabs.map(t=>t.code===code?{...t,...patch}:t)}));
 }
 function moveTab(code:string,direction:number){
  setDraft(old=>{
   if(!old)return old;
   const before=sorted(old.tabs),i=before.findIndex(x=>x.code===code);
   return {...old,tabs:move(before,i,direction).map((x,j)=>({...x,display_order:j}))};
  });
 }
 function updatePlacement(code:string,patch:Partial<FormPlacement>){
  setDraft(old=>old&&({...old,placements:old.placements.map(p=>p.metric_code===code?{...p,...patch}:p)}));
 }
 function movePlacement(code:string,direction:number){
  setDraft(old=>{
   if(!old)return old;
   const all=[...old.placements];
   const indexes=all.map((p,i)=>p.tab_code===selected?i:-1).filter(i=>i>=0);
   const position=indexes.findIndex(i=>all[i].metric_code===code);
   if(position<0||position+direction<0||position+direction>=indexes.length)return old;
   const a=indexes[position],b=indexes[position+direction];
   [all[a],all[b]]=[all[b],all[a]];
   return {...old,placements:all.map((p,i)=>({...p,display_order:i}))};
  });
 }
 function addTab(){
  if(!draft)return;
  const name=newTab.trim();if(name.length<2){setError('Nama tab minimal 2 karakter.');return;}
  const used=new Set(draft.tabs.map(x=>x.code));
  let code='tab_'+name.toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g,'_').replace(/^_+|_+$/g,'').slice(0,30);
  if(code.length<3)code='tab_baru';
  let suffix=2;const base=code;
  while(used.has(code))code=`${base.slice(0,35)}_${suffix++}`;
  if(draft.tabs.length>=30){setError('Maksimal 30 tab.');return;}
  setDraft({...draft,tabs:[...draft.tabs,{code,name,active:true,display_order:draft.tabs.length}]});
  setSelected(code);setNewTab('');setError('');
 }
 function reset(){if(saved){setDraft(clone(saved));setError('');setNotice('Perubahan yang belum disimpan dibatalkan.');}}
 async function save(){
  if(!draft)return;
  if(!draft.tabs.some(t=>t.active)){setError('Minimal satu tab harus aktif.');return;}
  setBusy(true);setError('');setNotice('');
  try{
   const payload={expected_version:draft.version,
    tabs:sorted(draft.tabs).map(({code,name,active})=>({code,name,active})),
    placements:[...draft.placements].sort((a,b)=>a.display_order-b.display_order)
      .map(({metric_code,tab_code,visible})=>({metric_code,tab_code,visible}))};
   const response=await api<InputFormConfig>('/input-form/config',{
    method:'PUT',body:JSON.stringify(payload)});
   setSaved(clone(response));setDraft(clone(response));setNotice('Tampilan input harian berhasil disimpan.');
  }catch(e){setError(errorText(e));}finally{setBusy(false)}
 }
 return <section className="panel input-layout-editor">
  <div className="panel-head"><div><h3>Atur Tab & Kolom Input Harian</h3><p className="muted small">Atur tampilan operator, bukan data atau rumus pengukuran.</p></div>
   <div className="toolbar-actions"><button className="btn secondary sm" onClick={reset} disabled={!dirty||busy}><RotateCcw size={15}/> Batal</button>
   <button className="btn primary sm" onClick={save} disabled={!dirty||busy}><Save size={15}/> Simpan Perubahan</button></div>
  </div>
  {error&&<div className="notice error" role="alert">{error}</div>}
  {notice&&<div className="notice success" role="status">{notice}</div>}
  <div className="input-layout-help">1. Buat atau pilih tab → 2. Pindahkan dan urutkan parameter → 3. Simpan → 4. Cek Input Beban Harian.</div>
  {!draft?<div className="empty">Memuat pengaturan...</div>:<div className="layout-editor-grid">
   <div className="layout-tab-side">
    <h4>Tab Formulir</h4>
    {tabs.map((t,i)=><div key={t.code} className={'layout-tab-row '+(selected===t.code?'selected':'')}>
      <button className="layout-tab-select" onClick={()=>setSelected(t.code)}>{t.name}<small>{t.code}</small></button>
      <button aria-label={`Naikkan ${t.name}`} title="Naikkan tab" disabled={i===0} onClick={()=>moveTab(t.code,-1)}><ArrowUp size={15}/></button>
      <button aria-label={`Turunkan ${t.name}`} title="Turunkan tab" disabled={i===tabs.length-1} onClick={()=>moveTab(t.code,1)}><ArrowDown size={15}/></button>
    </div>)}
    <div className="layout-add-tab"><input aria-label="Nama tab baru" value={newTab} onChange={e=>setNewTab(e.target.value)} placeholder="Nama tab baru" maxLength={100}/>
      <button className="btn secondary sm" onClick={addTab}><Plus size={15}/> Tambah</button></div>
   </div>
   <div className="layout-editor-main">
    {tabs.filter(t=>t.code===selected).map(t=><div key={t.code} className="layout-selected-tab">
     <div className="layout-tab-properties"><label>Nama tab<input value={t.name} onChange={e=>updateTab(t.code,{name:e.target.value})} maxLength={100}/></label>
     <label className="inline-check"><input type="checkbox" checked={t.active} onChange={e=>updateTab(t.code,{active:e.target.checked})}/> Tab aktif</label></div>
     <p className="muted small">Tab nonaktif tidak muncul di formulir harian. Parameter dan histori tetap tersimpan.</p>
    </div>)}
    <div className="layout-list-head"><h4>Kolom pada tab ini ({entries.length})</h4>
      <input aria-label="Cari parameter pada tab" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Cari parameter..."/></div>
    <div className="scroll-table"><table><thead><tr><th>Parameter</th><th>Jenis</th><th>Tab Tujuan</th><th>Ditampilkan</th><th>Urutan</th></tr></thead><tbody>
     {entries.map(({metric,placement},i)=><tr key={metric.code}>
      <td><strong>{metric.name}</strong><div className="muted small">{metric.code} · {metric.unit}{!metric.active?' · NONAKTIF':''}</div></td>
      <td>{metric.mode==='computed'?'Computed (otomatis)':metric.mode==='input'?'Input':'Imported'}</td>
      <td><select aria-label={`Tab untuk ${metric.name}`} value={placement.tab_code} onChange={e=>updatePlacement(metric.code,{tab_code:e.target.value})}>
       {tabs.map(x=><option key={x.code} value={x.code}>{x.name}</option>)}</select></td>
      <td><button className="layout-visibility" aria-label={`${placement.visible?'Sembunyikan':'Tampilkan'} ${metric.name}`} onClick={()=>updatePlacement(metric.code,{visible:!placement.visible})}>{placement.visible?<><Eye size={16}/> Ya</>:<><EyeOff size={16}/> Tidak</>}</button></td>
      <td><div className="layout-move-actions"><button aria-label={`Naikkan ${metric.name}`} disabled={i===0||Boolean(search)} onClick={()=>movePlacement(metric.code,-1)}><ArrowUp size={15}/></button><button aria-label={`Turunkan ${metric.name}`} disabled={i===entries.length-1||Boolean(search)} onClick={()=>movePlacement(metric.code,1)}><ArrowDown size={15}/></button></div></td>
     </tr>)}
    </tbody></table>{!entries.length&&<div className="empty">Tidak ada parameter di tab ini. Pindahkan parameter dari tab lainnya.</div>}</div>
    <div className="input-layout-preview"><h4>Pratinjau Formulir</h4><p>Kolom yang terlihat dalam tab ini:</p><div className="layout-preview-tags">{entries.filter(x=>x.placement.visible&&x.metric.active).slice(0,20).map(x=><span key={x.metric.code}>{x.metric.name} ({x.metric.unit})</span>)}{entries.filter(x=>x.placement.visible&&x.metric.active).length>20&&<span>…</span>}</div>
     <small>Parameter Computed otomatis read-only. Pengaturan ini tidak mengubah posisi sel saat import Excel.</small></div>
   </div>
  </div>}
 </section>;
}
