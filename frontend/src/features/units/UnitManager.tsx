import {useEffect,useMemo,useState} from 'react';
import {api} from '../../api';
import './units.css';

export type UnitItem={code:string;name:string;dimension:string;factor:number;active:boolean;builtin:boolean};
const DEFAULT_DIMENSIONS=[
 ['active_power','Daya aktif'],['apparent_power','Daya semu'],
 ['active_energy','Energi aktif'],['voltage','Tegangan'],['current','Arus'],
 ['frequency','Frekuensi'],['reactive_power','Daya reaktif'],
 ['reactive_energy','Energi reaktif'],['ratio','Rasio / Tanpa dimensi'],
];
const errorOf=(e:unknown)=>e instanceof Error?e.message:String(e);

export default function UnitManager(){
 const [items,setItems]=useState<UnitItem[]>([]);
 const [filter,setFilter]=useState('active');
 const [search,setSearch]=useState('');
 const [creating,setCreating]=useState(false);
 const [form,setForm]=useState({code:'',name:'',dimension:'active_power',factor:'1'});
 const [error,setError]=useState('');const [message,setMessage]=useState('');
 const [busy,setBusy]=useState(false);
 async function refresh(){setItems(await api<UnitItem[]>('/units'));}
 useEffect(()=>{refresh().catch(e=>setError(errorOf(e)));},[]);
 const visible=useMemo(()=>items.filter(u=>(filter==='all'||(filter==='active'?u.active:!u.active))&&
  `${u.name} ${u.code} ${u.dimension}`.toLowerCase().includes(search.toLowerCase())),[items,filter,search]);
 async function submit(e:React.FormEvent){e.preventDefault();setError('');setBusy(true);
  try{await api('/units',{method:'POST',body:JSON.stringify({...form,factor:Number(form.factor)})});
   await refresh();setCreating(false);setMessage('Satuan berhasil ditambahkan. Faktor dan dimensi tidak dapat diubah setelah dibuat.');
   setForm({code:'',name:'',dimension:'active_power',factor:'1'});
  }catch(err){setError(errorOf(err));}finally{setBusy(false);}
 }
 async function toggle(u:UnitItem){
  if(u.builtin||(!u.active&&!window.confirm(`Aktifkan satuan ${u.code}?`)))return;
  if(u.active&&!window.confirm(`Nonaktifkan ${u.code}? Satuan yang masih dipakai parameter akan ditolak.`))return;
  setError('');try{await api(`/units/${encodeURIComponent(u.code)}/status`,{method:'PUT',body:JSON.stringify({active:!u.active})});await refresh();}
  catch(err){setError(errorOf(err));}
 }
 return <section className="panel units-panel"><header className="units-header"><div><h3>Master Satuan & Konversi</h3>
 <p>Nilai historis tidak pernah dikonversi atau ditulis ulang. Konversi hanya untuk rumus baru dan tampilan grafik.</p></div>
 <button className="btn primary sm" onClick={()=>setCreating(true)}>+ Tambah Satuan</button></header>
 {message&&<div className="notice success">{message}</div>}{error&&<div className="notice error" role="alert">{error}</div>}
 <div className="units-filters"><input aria-label="Cari satuan" placeholder="Cari satuan atau kategori..." value={search} onChange={e=>setSearch(e.target.value)}/>
 <select aria-label="Status satuan" value={filter} onChange={e=>setFilter(e.target.value)}>
 <option value="active">Aktif</option><option value="inactive">Nonaktif</option><option value="all">Semua</option></select></div>
 <div className="scroll-table"><table><thead><tr><th>Satuan</th><th>Besaran</th><th>Faktor ke satuan dasar</th><th>Status</th><th>Aksi</th></tr></thead>
 <tbody>{visible.map(u=><tr key={u.code}><td><b>{u.code}</b><small className="units-sub">{u.name}</small></td>
 <td>{u.dimension}</td><td className="mono">{u.factor}</td>
 <td>{u.active?'Aktif':'Nonaktif'} {u.builtin?'· Bawaan':''}</td>
 <td>{u.builtin?<span className="muted">Terkunci</span>:<button className="link-btn" onClick={()=>toggle(u)}>{u.active?'Nonaktifkan':'Aktifkan'}</button>}</td></tr>)}</tbody></table>
 {!visible.length&&<div className="empty">Tidak ada satuan yang cocok.</div>}</div>
 <p className="muted small">Faktor harus mengacu ke satuan dasar dalam besaran yang sama. Misalnya MW=1000 dan kW=1, bukan konversi kW menjadi kVA.</p>
 {creating&&<div className="drawer-overlay" onMouseDown={e=>{if(e.target===e.currentTarget)setCreating(false)}}><aside className="parameter-drawer" role="dialog" aria-modal="true" aria-label="Tambah satuan">
 <div className="drawer-heading"><h3>Tambah Satuan</h3><button className="drawer-close" type="button" onClick={()=>setCreating(false)}>×</button></div>
 <form className="parameter-form drawer-body" onSubmit={submit}><label>Kode/simbol<input value={form.code} maxLength={12} required onChange={e=>setForm({...form,code:e.target.value})} placeholder="Contoh: kA"/></label>
 <label>Nama satuan<input value={form.name} minLength={2} required onChange={e=>setForm({...form,name:e.target.value})}/></label>
 <label>Jenis besaran<select value={form.dimension} onChange={e=>setForm({...form,dimension:e.target.value})}>
 {DEFAULT_DIMENSIONS.map(([code,name])=><option key={code} value={code}>{name}</option>)}
 <option value="other_custom">Lainnya (tidak bisa dikonversi dengan besaran lain)</option></select></label>
 <label>Faktor terhadap satuan dasar<input type="number" min="0.000000000001" step="any" required value={form.factor} onChange={e=>setForm({...form,factor:e.target.value})}/></label>
 <p className="parameter-hint">Pembuatan satuan tidak dapat diubah faktor/dimensinya setelah disimpan. Periksa dengan cermat sebelum mengaktifkan.</p>
 <div className="units-buttons"><button className="btn secondary" type="button" onClick={()=>setCreating(false)}>Batal</button><button className="btn primary" disabled={busy}>Simpan Satuan</button></div>
 </form></aside></div>}
 </section>;
}
