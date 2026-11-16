import {useEffect,useState,type FormEvent} from 'react';
import {Pencil,Plus,X} from 'lucide-react';
import {api,type Catalog,type EquipmentKind} from '../../api';
import ListControls,{PAGE_SIZE} from '../../shared/ListControls';
import '../parameters/parameters.css';

const info=(e:unknown)=>e instanceof Error?e.message:String(e);
const codeFrom=(s:string)=>s.toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^_+|_+$/g,'');

export default function EquipmentKinds({catalog}:{catalog:Catalog}){
  const [items,setItems]=useState<EquipmentKind[]>([]);
  const [editing,setEditing]=useState<EquipmentKind|null>(null);
  const [open,setOpen]=useState(false);
  const [name,setName]=useState('');
  const [code,setCode]=useState('');
  const [active,setActive]=useState(true);
  const [search,setSearch]=useState('');
  const [status,setStatus]=useState('active');
  const [page,setPage]=useState(1);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');
  const refresh=()=>api<EquipmentKind[]>('/equipment-kinds').then(setItems);
  useEffect(()=>{refresh().catch(e=>setError(info(e)))},[]);
  const filtered=items.filter(item=>(status==='all'||item.active===(status==='active'))&&
    `${item.name} ${item.code}`.toLowerCase().includes(search.toLowerCase()));
  const paged=filtered.slice((page-1)*PAGE_SIZE,page*PAGE_SIZE);
  const startCreate=()=>{setEditing(null);setName('');setCode('');setActive(true);setError('');setOpen(true)};
  const startEdit=(item:EquipmentKind)=>{setEditing(item);setName(item.name);setCode(item.code);
    setActive(item.active);setError('');setOpen(true)};
  async function submit(event:FormEvent){
    event.preventDefault();setBusy(true);setError('');
    try{
      if(editing){await api(`/equipment-kinds/${editing.id}`,{method:'PUT',body:JSON.stringify({name:name.trim(),active})});}
      else{await api('/equipment-kinds',{method:'POST',body:JSON.stringify({name:name.trim(),code:code.trim()})});}
      await refresh();setOpen(false);setNotice('Jenis peralatan berhasil disimpan.');
    }catch(e){setError(info(e))}finally{setBusy(false)}
  }
  return <section className="panel">
    <div className="panel-head parameter-toolbar"><div><h3>Master Jenis Peralatan</h3>
      <p>Kategori dapat ditambah dan diganti namanya; kode lama tetap dipertahankan.</p></div>
      <button type="button" className="btn primary sm" onClick={startCreate}><Plus size={16}/> Tambah Jenis</button></div>
    {notice&&<div className="notice success">{notice}</div>}
    <ListControls search={search} onSearch={setSearch} status={status} onStatus={setStatus}
      options={[{value:'active',label:'Aktif'},{value:'inactive',label:'Nonaktif'},{value:'all',label:'Semua'}]}
      page={page} onPage={setPage} count={filtered.length}/>
    <div className="scroll-table"><table><thead><tr><th>Nama Jenis</th><th>Kode</th><th>Peralatan</th>
      <th>Status</th><th>Aksi</th></tr></thead><tbody>
      {paged.map(item=><tr key={item.id}><td><strong>{item.name}</strong></td>
        <td className="mono">{item.code}</td>
        <td>{catalog.assets.filter(a=>a.kind===item.code).length}</td>
        <td><span className={'tag '+(item.active?'success':'warning')}>
          {item.active?'Aktif':'Nonaktif'}</span></td>
        <td><button type="button" className="link-btn" onClick={()=>startEdit(item)}>
          <Pencil size={14}/> Ubah</button></td></tr>)}
    </tbody></table>{!filtered.length&&<div className="empty">Tidak ada kategori yang cocok.</div>}</div>
    <p className="parameter-hint">Menonaktifkan jenis tidak mengubah kategori peralatan yang sudah ada dan
      tidak menghapus data historis. Jenis nonaktif tidak dapat dipilih untuk peralatan baru.</p>
    {open&&<div className="drawer-overlay" onMouseDown={e=>{if(e.target===e.currentTarget&&!busy)setOpen(false)}}>
      <aside className="parameter-drawer" role="dialog" aria-modal="true" aria-label="Edit jenis peralatan">
        <div className="drawer-heading"><h3>{editing?'Ubah Jenis':'Tambah Jenis Peralatan'}</h3>
          <button className="drawer-close" type="button" disabled={busy} aria-label="Tutup"
            onClick={()=>setOpen(false)}><X size={20}/></button></div>
        <div className="drawer-body"><form className="parameter-form" onSubmit={submit}>
          <label>Nama jenis<input required minLength={2} maxLength={100} autoFocus value={name}
            onChange={e=>{setName(e.target.value);if(!editing)setCode(codeFrom(e.target.value))}}/></label>
          <label>Kode unik<input required disabled={Boolean(editing)} minLength={2} maxLength={35}
            pattern="[a-z][a-z0-9_]*" value={code} onChange={e=>setCode(e.target.value.toLowerCase())}/></label>
          {editing&&<label className="parameter-active"><input type="checkbox" checked={active}
            onChange={e=>setActive(e.target.checked)}/> Jenis aktif</label>}
          {error&&<div className="notice error" role="alert">{error}</div>}
          <button type="submit" className="btn primary" disabled={busy}>
            {busy?'Menyimpan...':'Simpan Jenis'}</button>
          <button type="button" className="btn secondary" disabled={busy} onClick={()=>setOpen(false)}>Batal</button>
        </form></div>
      </aside></div>}
  </section>;
}
