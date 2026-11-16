import {useEffect,useState} from 'react';
import {api,type Catalog} from '../../api';

type Selection={unit_id:number;configured:boolean;load_code:string|null;capacity_code:string|null};
const errorText=(e:unknown)=>e instanceof Error?e.message:String(e);

export default function PrimaryMetricSettings({catalog,refreshCatalog}:{catalog:Catalog;refreshCatalog:()=>void}){
 const [saved,setSaved]=useState<Selection|null>(null);
 const [load,setLoad]=useState(''),[capacity,setCapacity]=useState('');
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('');
 function refresh(){api<Selection>('/primary-metrics').then(s=>{
   setSaved(s);setLoad(s.load_code||'');setCapacity(s.capacity_code||'');
 }).catch(e=>setError(errorText(e)))}
 useEffect(()=>{refresh()},[]);
 const options=catalog.metrics.filter(m=>m.active&&m.unit_id===saved?.unit_id&&m.code!=='daya_mampu_sistem_kw');
 async function save(){
  if(load&&load===capacity){setError('Parameter beban dan daya mampu harus berbeda.');return;}
  setBusy(true);setError('');setMessage('');
  try{
   await api('/primary-metrics',{method:'PUT',body:JSON.stringify({load_code:load||null,capacity_code:capacity||null})});
   refreshCatalog();refresh();setMessage('Parameter utama unit berhasil diperbarui.');
  }catch(e){setError(errorText(e))}finally{setBusy(false)}
 }
 return <section className="panel"><div className="panel-head"><h3>Parameter utama unit</h3></div>
  <p className="muted">Tetapkan parameter beban sistem dan daya mampu pada ULP Tanjung Redeb. Grafik H/J dan laporan bawaan mengikuti kunci peran, bukan kode parameter. Konfigurasi historis tersimpan tidak diubah.</p>
  {saved&&<div className="stats-list"><div><span>Unit ID</span><b>{saved.unit_id}</b></div>
  <div><span>Status</span><b>{saved.configured?'Lengkap':'Parameter utama belum diatur'}</b></div></div>}
  <div className="user-form"><div className="field"><label>Beban Sistem (system.load)</label><select value={load} onChange={e=>setLoad(e.target.value)}><option value="">Belum diatur</option>{options.filter(m=>m.role_key==null||m.role_key==='system.load'||m.role_key==='system.capacity'||m.code===load).map(m=><option key={m.id} value={m.code}>{m.name} ({m.code}) · {m.unit}</option>)}</select></div>
   <div className="field"><label>Daya Mampu (system.capacity)</label><select value={capacity} onChange={e=>setCapacity(e.target.value)}><option value="">Belum diatur</option>{options.filter(m=>m.role_key==null||m.role_key==='system.load'||m.role_key==='system.capacity'||m.code===capacity).map(m=><option key={m.id} value={m.code}>{m.name} ({m.code}) · {m.unit}</option>)}</select></div>
  <button className="btn primary" type="button" disabled={busy||!saved} onClick={save}>{busy?'Menyimpan…':'Simpan Parameter Utama'}</button></div>
  {error&&<p className="notice error" role="alert">{error}</p>}{message&&<p className="notice success">{message}</p>}
 </section>
}
