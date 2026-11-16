import {useEffect,useMemo,useRef,useState} from 'react';
import {Archive,Check,Copy,Grip,LayoutDashboard,Plus,RotateCcw,Save,Settings2,Star,X} from 'lucide-react';
import {api,isoWita,type Catalog,type User} from '../../api';
import PanelCard from './PanelCard';
import PanelEditor from './PanelEditor';
import DashboardManagement from './DashboardManagement';
import type {DashLayout,DashPanel,LayoutList,PaneContext,HistoricalOption,RuleOption} from './types';
import {defaultPanel} from './types';
import type {UnitItem} from '../units/UnitManager';
import './dashboard-builder.css';

const msg=(err:unknown)=>err instanceof Error?err.message:String(err);
const today=isoWita();
function initPeriod(){return {mode:'month',start:today.slice(0,8)+'01',end:today,granularity:'day' as PaneContext['granularity']};}
function periodOf(mode:string,customStart:string,customEnd:string,customGrain:PaneContext['granularity']){
  const y=Number(today.slice(0,4)),m=Number(today.slice(5,7));
  if(mode==='day')return {start:today,end:today,granularity:'hour' as const};
  if(mode==='month')return {start:`${y}-${String(m).padStart(2,'0')}-01`,end:today,granularity:'day' as const};
  if(mode==='year')return {start:`${y}-01-01`,end:today,granularity:'month' as const};
  return {start:customStart,end:customEnd,granularity:customGrain};
}

export default function DashboardBuilder({catalog,user}:{catalog:Catalog;user:User}){
  const [list,setList]=useState<LayoutList|null>(null);
  const [selectedId,setSelectedId]=useState<number|null>(null);
  const [draft,setDraft]=useState<DashLayout|null>(null);
  const [editing,setEditing]=useState(false);
  const [dirty,setDirty]=useState(false);
  const [panelEdit,setPanelEdit]=useState<DashPanel|null>(null);
  const [creating,setCreating]=useState(false);
  const [newName,setNewName]=useState('Dashboard Pribadi');
  const [newScope,setNewScope]=useState<'personal'|'system'>('personal');
  const [period,setPeriod]=useState(initPeriod);
  const [historical,setHistorical]=useState<HistoricalOption[]>([]);
  const [rules,setRules]=useState<RuleOption[]>([]);
  const [units,setUnits]=useState<UnitItem[]>([]);
  const [error,setError]=useState('');const [notice,setNotice]=useState('');
  const [busy,setBusy]=useState(false);
  const dragged=useRef<string|null>(null);
  const effective=periodOf(period.mode,period.start,period.end,period.granularity);
  const ctx=useMemo<PaneContext>(()=>({...effective,catalog,units}),[effective.start,effective.end,effective.granularity,catalog,units]);
  const canEdit=!!draft&&(draft.scope==='personal'?draft.owner_id===user.id:user.role==='admin');

  async function refresh(preferred?:number){
    const data=await api<LayoutList>('/dashboard-builder');
    setList(data);
    const id=preferred??selectedId??data.effective_default_id??data.items[0]?.id;
    const item=data.items.find(d=>d.id===id)||data.items[0]||null;
    setSelectedId(item?.id??null);setDraft(item?structuredClone(item):null);
    setDirty(false);setEditing(false);
  }
  useEffect(()=>{refresh().catch(e=>setError(msg(e)));
    api<HistoricalOption[]>('/historical-calculations').then(setHistorical).catch(()=>{});
    api<RuleOption[]>('/engineering-rules').then(setRules).catch(()=>{});
    api<UnitItem[]>('/units').then(setUnits).catch(()=>{});
  },[]);
  useEffect(()=>{if(!dirty)return;
    const handler=(event:BeforeUnloadEvent)=>{event.preventDefault()};
    window.addEventListener('beforeunload',handler);
    return()=>window.removeEventListener('beforeunload',handler);
  },[dirty]);

  function cancelEdit(){
    if(dirty&&!window.confirm('Batalkan perubahan dashboard yang belum disimpan?'))return;
    const saved=list?.items.find(v=>v.id===selectedId)||null;
    setDraft(saved?structuredClone(saved):null);
    setEditing(false);setDirty(false);setPanelEdit(null);setError('');
    setNotice('Perubahan yang belum disimpan dibatalkan.');
  }
  function resetDraft(){
    if(!draft||!window.confirm('Kembalikan layout dan nama ke versi tersimpan?'))return;
    const saved=list?.items.find(v=>v.id===selectedId);
    if(saved){setDraft(structuredClone(saved));setDirty(false);setPanelEdit(null);}
  }
  useEffect(()=>{
    if(!dirty)return;
    const handler=()=>{
      if(window.location.hash==='#/builder')return;
      if(!window.confirm('Perubahan dashboard belum disimpan. Tinggalkan halaman?')){
        window.location.hash='/builder';
      }
    };
    window.addEventListener('hashchange',handler);
    return()=>window.removeEventListener('hashchange',handler);
  },[dirty]);
  function switchDash(id:number){
    if(dirty&&!window.confirm('Perubahan dashboard belum disimpan. Abaikan perubahan?'))return;
    const item=list?.items.find(v=>v.id===id)||null;
    setSelectedId(id);setDraft(item?structuredClone(item):null);
    setEditing(false);setDirty(false);setError('');setNotice('');
  }
  function change(patch:Partial<DashLayout>){setDraft(old=>old?{...old,...patch}:null);setDirty(true)}
  function editPanel(value:DashPanel){if(!draft)return;
    const exists=draft.panels.some(p=>p.id===value.id);
    change({panels:exists?draft.panels.map(p=>p.id===value.id?value:p):[...draft.panels,value]});
    setPanelEdit(null);
  }
  function remove(id:string){if(!draft||!window.confirm('Hapus panel ini dari layout? Data pengukuran tidak terhapus.'))return;
    change({panels:draft.panels.filter(p=>p.id!==id)});
  }
  function move(id:string,direction:number){if(!draft)return;
    const next=[...draft.panels],from=next.findIndex(p=>p.id===id),to=from+direction;
    if(from<0||to<0||to>=next.length)return;
    const [item]=next.splice(from,1);next.splice(to,0,item);change({panels:next});
  }
  function drop(target:string){const source=dragged.current;dragged.current=null;
    if(!draft||!source||source===target)return;
    const next=[...draft.panels],from=next.findIndex(p=>p.id===source),to=next.findIndex(p=>p.id===target);
    if(from<0||to<0)return;
    const [item]=next.splice(from,1);next.splice(to,0,item);change({panels:next});dragged.current=null;
  }
  async function save(){if(!draft)return;
    setBusy(true);setError('');
    try{
      const updated=await api<DashLayout>(`/dashboard-builder/${draft.id}`,{method:'PUT',body:JSON.stringify({
        name:draft.name,description:draft.description,panels:draft.panels,expected_version:draft.version,
      })});
      await refresh(updated.id);setNotice('Dashboard berhasil disimpan.');
    }catch(e){setError(msg(e))}finally{setBusy(false)}
  }
  async function action(path:string,method='POST',payload?:object){
    setBusy(true);setError('');setNotice('');
    try{const result=await api<DashLayout|{ok:boolean}>(path,{method,body:payload?JSON.stringify(payload):undefined});
      await refresh('id' in result?result.id:undefined);
      setCreating(false);setNotice('Perubahan berhasil disimpan.');
    }catch(e){setError(msg(e))}finally{setBusy(false)}
  }
  function runAction(path:string,confirmText?:string){
    if(dirty&&!window.confirm('Perubahan belum disimpan. Lanjut dan abaikan perubahan?'))return;
    if(confirmText&&!window.confirm(confirmText))return;
    action(path);
  }
  const maxHours=effective.granularity==='hour'?(Date.parse(effective.end)-Date.parse(effective.start))/86400000:0;
  const validPeriod=!!effective.start&&!!effective.end&&effective.start<=effective.end&&maxHours<=30;
  return <div className="page-space dashboard-builder">
    <div className="page-top"><div><div className="eyebrow">MONITORING • LAYOUT KUSTOM</div>
      <h2>Dashboard Builder</h2><p>Buat panel sendiri tanpa Python atau SQL. Sumbernya tetap pengukuran Berau.</p></div>
      <button type="button" className="btn primary" onClick={()=>setCreating(v=>!v)}><Plus size={17}/> Dashboard Baru</button></div>
    <div className="dash-toolbar panel"><div className="dash-toolbar-left"><label>Dashboard<select value={selectedId||''} onChange={e=>switchDash(Number(e.target.value))}>
      {(list?.items||[]).map(v=><option key={v.id} value={v.id}>{v.name} · {v.scope==='system'?'Sistem':'Pribadi'}</option>)}</select></label>
      <label>Periode<select value={period.mode} onChange={e=>setPeriod(p=>({...p,mode:e.target.value}))}>
        <option value="day">Hari Ini (24 Jam)</option><option value="month">Bulan Ini</option><option value="year">Tahun Ini</option><option value="custom">Rentang Khusus</option></select></label>
      {period.mode==='custom'&&<><label>Mulai<input type="date" value={period.start} onChange={e=>setPeriod(p=>({...p,start:e.target.value}))}/></label>
        <label>Sampai<input type="date" value={period.end} onChange={e=>setPeriod(p=>({...p,end:e.target.value}))}/></label>
        <label>Resolusi<select value={period.granularity} onChange={e=>setPeriod(p=>({...p,granularity:e.target.value as PaneContext['granularity']}))}>
          <option value="hour">Jam</option><option value="day">Hari</option><option value="month">Bulan</option><option value="year">Tahun</option></select></label></>}
    </div>
    <div className="dash-toolbar-actions">
      {draft&&<><button className="btn secondary sm" onClick={()=>runAction(`/dashboard-builder/${draft.id}/duplicate`)} disabled={busy}><Copy size={15}/> Duplikat</button>
        {canEdit&&<button className="btn secondary sm" onClick={()=>runAction(`/dashboard-builder/${draft.id}/default`)} disabled={busy||draft.is_default}><Star size={15}/> {draft.is_default?'Default':'Jadikan Default'}</button>}
        {canEdit&&!editing&&<button className="btn secondary sm" onClick={()=>{setEditing(true);setNotice('')}}><Settings2 size={15}/> Edit Layout</button>}
        {canEdit&&editing&&<button className="btn secondary sm" onClick={cancelEdit} disabled={busy}><X size={15}/> Batal</button>}
      </>}
    </div></div>
    <DashboardManagement layout={draft} editable={canEdit}
      onBeforeAction={()=>!dirty||window.confirm('Ada perubahan layout belum tersimpan. Abaikan perubahan?')}
      onChanged={id=>refresh(id).catch(e=>setError(msg(e)))}/>
    {creating&&<div className="panel dash-create"><strong>Buat Dashboard Baru</strong><label>Nama<input value={newName} onChange={e=>setNewName(e.target.value)}/></label>
      {user.role==='admin'&&<label>Jenis<select value={newScope} onChange={e=>setNewScope(e.target.value as 'personal'|'system')}><option value="personal">Pribadi</option><option value="system">Sistem (untuk semua pengguna)</option></select></label>}
      <button className="btn primary sm" disabled={busy||newName.trim().length<3} onClick={()=>action('/dashboard-builder','POST',{name:newName,scope:newScope,panels:[]})}><Plus size={15}/> Buat</button>
      <button className="btn secondary sm" onClick={()=>setCreating(false)}>Batal</button></div>}
    {error&&<div className="notice error" role="alert">{error}</div>}{notice&&<div className="notice success" role="status">{notice}</div>}
    {!validPeriod&&<div className="notice error">Periode tidak valid; resolusi jam maksimal 31 hari.</div>}
    {draft&&<><div className="dash-heading"><div>{editing?<><label>Nama Dashboard<input value={draft.name} onChange={e=>change({name:e.target.value})}/></label>
      <label>Deskripsi<input value={draft.description} onChange={e=>change({description:e.target.value})}/></label></>:
      <><h3>{draft.name}</h3><p>{draft.description}</p></>}</div>
      {editing&&<div className="dash-edit-actions"><button className="btn secondary sm" onClick={()=>setPanelEdit({...defaultPanel(catalog.roles?.['system.load']||''),title:''})} disabled={draft.panels.length>=16}><Plus size={15}/> Tambah Panel</button>
        <button className="btn primary sm" onClick={save} disabled={!dirty||busy}><Save size={15}/> Simpan Perubahan</button>
        <button className="btn secondary sm" onClick={resetDraft} disabled={!dirty||busy}><RotateCcw size={15}/> Reset ke Tersimpan</button>
        <button className="btn secondary sm" onClick={()=>runAction(`/dashboard-builder/${draft.id}/archive`,'Arsipkan dashboard ini? Panel dan data asli tetap aman.')} disabled={busy}><Archive size={15}/> Arsipkan</button></div>}
    </div>
    {validPeriod&&<div className="dash-grid">{draft.panels.map((panel,i)=><PanelCard key={panel.id} panel={panel} ctx={ctx} editing={editing}
      onEdit={()=>setPanelEdit(panel)} onRemove={()=>remove(panel.id)} onMove={step=>move(panel.id,step)}
      onResize={(w,h)=>change({panels:draft.panels.map(p=>p.id===panel.id?{...p,w,h}:p)})}
      onDragStart={e=>{dragged.current=panel.id;e.dataTransfer.effectAllowed='move'}}
      onDragEnd={()=>{dragged.current=null}} onDrop={e=>{e.preventDefault();drop(panel.id)}}/>)}</div>}
    {draft.panels.length===0&&<div className="panel dash-empty"><Grip size={25}/><p>Dashboard belum memiliki panel.</p>
      {canEdit&&<button className="btn primary" onClick={()=>{setEditing(true);setPanelEdit({...defaultPanel(catalog.roles?.['system.load']||''),title:''})}}>Tambah Panel Pertama</button>}</div>}
    {editing&&<p className="dash-tip"><Check size={15}/> Tarik ikon pegangan untuk memindahkan, dan sudut kanan bawah untuk mengubah lebar/tinggi. Simpan atau Batal setelah selesai.</p>}
    <p className="dash-tip">Grafik ini berdasarkan data terakhir yang tersimpan, bukan telemetri SCADA real-time. H/J selalu mengacu kolom H dan J rekap Excel.</p>
    </>}
    {!draft&&<div className="panel dash-empty"><LayoutDashboard size={26}/> Memuat dashboard atau belum tersedia.</div>}
    {panelEdit&&<PanelEditor initial={panelEdit} catalog={catalog} historical={historical} rules={rules} onClose={()=>setPanelEdit(null)} onSave={editPanel}/>}
  </div>;
}
