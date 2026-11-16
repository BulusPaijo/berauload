import {useEffect,useState} from 'react';
import {Archive,Download,History,Share2,Upload,LayoutTemplate,RotateCcw} from 'lucide-react';
import {api,apiFetch} from '../../api';
import type {DashLayout} from './types';

type Revision={id:number;version:number;created_at:string;updated_by:number|null;snapshot:{name:string;description:string;panels:unknown[]}};
type Preset={key:string;name:string};
const err=(e:unknown)=>e instanceof Error?e.message:String(e);

export default function DashboardManagement({layout,editable,onChanged,onBeforeAction}:{
  layout:DashLayout|null;editable:boolean;onChanged:(id:number)=>void;onBeforeAction:()=>boolean;
}){
  const [open,setOpen]=useState(false),[revisions,setRevisions]=useState<Revision[]>([]);
  const [shares,setShares]=useState<string[]>([]),[username,setUsername]=useState('');
  const [presets,setPresets]=useState<Preset[]>([]),[preset,setPreset]=useState('operasi');
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
  useEffect(()=>{api<Preset[]>('/dashboard-builder/manage/templates').then(items=>{setPresets(items);if(items.length)setPreset(items[0].key)}).catch(()=>{});},[]);
  useEffect(()=>{if(!open||!layout)return;
    api<Revision[]>(`/dashboard-builder/${layout.id}/revisions`).then(setRevisions).catch(()=>{});
    if(editable&&layout.scope==='personal')api<string[]>(`/dashboard-builder/${layout.id}/shares`).then(setShares).catch(()=>{});
  },[open,layout?.id,layout?.version,editable]);
  async function run(work:()=>Promise<unknown>,label:string){if(!onBeforeAction())return;
    setBusy(true);setError('');setNotice('');try{const result=await work();
      if(result&&typeof result==='object'&&'id' in result){onChanged(Number(result.id))}else if(layout)onChanged(layout.id);
      setNotice(label);
    }catch(e){setError(err(e))}finally{setBusy(false)}}
  async function exportJson(){if(!layout)return;
    setBusy(true);setError('');try{const r=await apiFetch(`/api/dashboard-builder/${layout.id}/export-config`,{credentials:'same-origin'});
      if(!r.ok)throw new Error(`HTTP ${r.status}`);
      const blob=await r.blob(),url=URL.createObjectURL(blob),a=document.createElement('a');
      a.href=url;a.download=`dashboard-berauload-${layout.id}.json`;document.body.append(a);a.click();a.remove();URL.revokeObjectURL(url);
    }catch(e){setError(err(e))}finally{setBusy(false)}}
  async function importJson(file:File|undefined){if(!file)return;
    if(file.size>100_000)return setError('File terlalu besar, maksimal 100 KB');
    try{const obj=JSON.parse(await file.text());
      if(obj.format!=='berauload-dashboard-v1'||!Array.isArray(obj.panels))throw new Error('Bukan konfigurasi dashboard BerauLoad');
      await run(()=>api<DashLayout>('/dashboard-builder/import-config',{method:'POST',body:JSON.stringify({name:obj.name,description:obj.description||'',panels:obj.panels})}),
        'Konfigurasi diimpor sebagai dashboard pribadi.');
    }catch(e){setError(err(e))}}
  async function addShare(){if(!layout||!username.trim())return;
    await run(async()=>{const r=await api(`/dashboard-builder/${layout.id}/shares`,{method:'POST',body:JSON.stringify({username:username.trim()})});
      setShares(await api<string[]>(`/dashboard-builder/${layout.id}/shares`));setUsername('');return r},'Akses baca-saja diberikan.');}
  async function revoke(name:string){if(!layout||!window.confirm(`Hentikan akses ${name}?`))return;
    await run(async()=>{const r=await api(`/dashboard-builder/${layout.id}/shares/${encodeURIComponent(name)}`,{method:'DELETE'});
      setShares(await api<string[]>(`/dashboard-builder/${layout.id}/shares`));return r},'Akses dibatalkan.');}
  return <section className="dash-manage panel">
    <div className="dash-manage-header"><div><strong>Kelola Dashboard</strong><p className="muted small">Template, berbagi, JSON konfigurasi, dan riwayat versi</p></div>
      <button className="btn secondary sm" onClick={()=>setOpen(v=>!v)}>{open?'Tutup Pengaturan':'Buka Pengaturan'}</button></div>
    {open&&<div className="dash-manage-content">
      {error&&<div className="notice error" role="alert">{error}</div>}{notice&&<div className="notice success">{notice}</div>}
      <div className="dash-manage-group"><h4><LayoutTemplate size={16}/> Template Bawaan</h4>
        <div className="dash-manage-row"><select value={preset} onChange={e=>setPreset(e.target.value)}>
          {presets.map(p=><option key={p.key} value={p.key}>{p.name}</option>)}</select>
          <button className="btn secondary sm" disabled={busy||!preset} onClick={()=>run(()=>api<DashLayout>(`/dashboard-builder/manage/templates/${preset}/create`,{method:'POST'}),'Dashboard pribadi dari template berhasil dibuat.')}>Buat Dashboard dari Template</button></div>
      </div>
      <div className="dash-manage-group"><h4><Download size={16}/> Ekspor / Impor Layout</h4>
        <div className="dash-manage-row"><button className="btn secondary sm" disabled={!layout||busy} onClick={exportJson}>Unduh Konfigurasi JSON</button>
          <label className="dash-file-input"><Upload size={15}/> Impor JSON<input type="file" accept=".json,application/json" disabled={busy}
            onChange={e=>{importJson(e.target.files?.[0]);e.target.value=''}}/></label></div>
        <p className="muted small">Yang disimpan hanya konfigurasi panel; tidak termasuk data listrik, akun, atau password. Import selalu membuat dashboard pribadi baru.</p>
      </div>
      {layout&&<div className="dash-manage-group"><h4><History size={16}/> Riwayat Layout</h4>
        <div className="dash-revisions">{revisions.map(r=><div key={r.id} className="dash-revision">
          <div><b>Versi {r.version}</b><small>{new Date(r.created_at).toLocaleString('id-ID',{timeZone:'Asia/Makassar'})} WITA · {r.snapshot.panels.length} panel</small></div>
          {editable&&r.version!==layout.version&&<button className="btn secondary sm" disabled={busy}
            onClick={()=>{
              if(!window.confirm(`Pulihkan layout versi ${r.version}? Versi saat ini tetap tersimpan.`))return;
              run(()=>api<DashLayout>(`/dashboard-builder/${layout.id}/restore-version`,{
                method:'POST',body:JSON.stringify({revision_id:r.id,expected_version:layout.version}),
              }),`Layout versi ${r.version} dipulihkan sebagai versi baru.`);
            }}><RotateCcw size={14}/> Pulihkan</button>}</div>)}
          {!revisions.length&&<p className="muted small">Belum ada revisi.</p>}</div>
      </div>}
      {layout&&editable&&layout.scope==='personal'&&<div className="dash-manage-group"><h4><Share2 size={16}/> Bagikan Dashboard (Baca-Saja)</h4>
        <div className="dash-manage-row"><input placeholder="Username pengguna" value={username} onChange={e=>setUsername(e.target.value)}/>
          <button className="btn secondary sm" disabled={busy||!username.trim()} onClick={addShare}>Bagikan</button></div>
        <div className="dash-shares">{shares.map(name=><div key={name}><span>{name}</span><button className="btn secondary sm" disabled={busy} onClick={()=>revoke(name)}>Cabut Akses</button></div>)}
          {!shares.length&&<small>Belum dibagikan ke pengguna lain.</small>}</div></div>}
      {layout&&editable&&<p className="muted small"><Archive size={13} style={{verticalAlign:'middle'}}/> Untuk mengarsipkan dashboard, gunakan tombol Arsipkan dalam mode Edit Layout.</p>}
    </div>}
  </section>;
}
