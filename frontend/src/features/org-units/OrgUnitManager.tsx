import {useEffect,useState,type FormEvent,type ReactNode} from 'react';
import {api} from '../../api';
import UnitAccess from './UnitAccess';
import CopySettings from './CopySettings';
import './org-units.css';

export type OrgUnit={id:number;code:string;name:string;level:'up3'|'ulp'|'kp';
 parent_id:number|null;active:boolean;display_order:number;children:OrgUnit[]};
const message=(e:unknown)=>e instanceof Error?e.message:String(e);
const labels={up3:'UP3',ulp:'ULP',kp:'KP'};

export default function OrgUnitManager(){
 const [tree,setTree]=useState<OrgUnit[]>([]);
 const [selected,setSelected]=useState<number|null>(null);
 const [action,setAction]=useState<'create'|'edit'|null>(null);
 const [level,setLevel]=useState<'ulp'|'kp'>('ulp');
 const [parent,setParent]=useState<number|null>(null);
 const [code,setCode]=useState('');
 const [name,setName]=useState('');
 const [order,setOrder]=useState(0);
 const [error,setError]=useState('');
 const [notice,setNotice]=useState('');
 const [busy,setBusy]=useState(false);
 function flatten(rows:OrgUnit[]):OrgUnit[]{return rows.flatMap(u=>[u,...flatten(u.children)]);}
 const all=flatten(tree);
 const current=all.find(u=>u.id===selected);
 async function reload(){const rows=await api<OrgUnit[]>('/org-units');setTree(rows);
  setSelected(id=>id&&flatten(rows).some(u=>u.id===id)?id:rows[0]?.id??null);}
 useEffect(()=>{reload().catch(e=>setError(message(e)))},[]);
 function prepareCreate(parentUnit:OrgUnit){
  if(parentUnit.level==='kp'||!parentUnit.active)return;
  setAction('create');setParent(parentUnit.id);
  setLevel(parentUnit.level==='up3'?'ulp':'kp');
  setCode('');setName('');setOrder(0);setError('');setNotice('');
 }
 function prepareEdit(unit:OrgUnit){
  setSelected(unit.id);setAction('edit');setName(unit.name);setCode(unit.code);
  setOrder(unit.display_order);setError('');setNotice('');
 }
 async function save(event:FormEvent){
  event.preventDefault();setBusy(true);setError('');setNotice('');
  try{
   if(action==='create')await api('/org-units',{method:'POST',body:JSON.stringify({
    parent_id:parent,level,code:code.trim(),name:name.trim(),display_order:order})});
   else if(current)await api(`/org-units/${current.id}`,{method:'PUT',
    body:JSON.stringify({name:name.trim(),display_order:order})});
   await reload();setAction(null);setNotice('Struktur organisasi berhasil disimpan.');
  }catch(e){setError(message(e))}finally{setBusy(false)}
 }
 async function toggle(unit:OrgUnit){
  if(!window.confirm(`${unit.active?'Nonaktifkan':'Aktifkan'} ${unit.name}?`))return;
  setError('');setNotice('');
  try{await api(`/org-units/${unit.id}/status`,{method:'PUT',
   body:JSON.stringify({active:!unit.active})});await reload();
   setNotice('Status unit berhasil diperbarui.');
  }catch(e){setError(message(e))}
 }
 function branch(unit:OrgUnit,depth=0):ReactNode{
  return <div key={unit.id} className="org-branch">
   <div className={'org-unit-line '+(selected===unit.id?'selected':'')}
    style={{paddingLeft:12+depth*22}}>
    <button type="button" className="org-unit-select" onClick={()=>{setSelected(unit.id);setAction(null)}}>
     <strong>{labels[unit.level]} · {unit.name}</strong>
     <small>{unit.code}{!unit.active?' · Nonaktif':''}</small>
    </button>
    <div className="org-unit-actions">
     <button type="button" onClick={()=>prepareEdit(unit)}>Ubah</button>
     {unit.level!=='kp'&&unit.active&&<button type="button"
      onClick={()=>prepareCreate(unit)}>+ {unit.level==='up3'?'ULP':'KP'}</button>}
     {unit.level!=='up3'&&<button type="button" onClick={()=>toggle(unit)}>
      {unit.active?'Nonaktifkan':'Aktifkan'}</button>}
    </div>
   </div>
   {unit.children.map(child=>branch(child,depth+1))}
  </div>;
 }
 return <section className="panel org-manager">
  <div className="panel-head"><div><h3>Struktur Organisasi</h3>
   <p>Pohon UP3 → ULP → KP. Data historis lama tetap milik ULP Tanjung Redeb.</p></div></div>
  {error&&<div role="alert" className="notice error">{error}</div>}
  {notice&&<div role="status" className="notice success">{notice}</div>}
  <div className="org-columns">
   <div className="org-tree" aria-label="Pohon struktur organisasi">{tree.map(u=>branch(u))}</div>
   <div className="org-side">
    {action&&<form className="org-form" onSubmit={save}>
     <h4>{action==='create'?`Tambah ${labels[level]}`:'Ubah Unit'}</h4>
     <label>Nama unit<input required minLength={2} maxLength={180} value={name}
      onChange={e=>setName(e.target.value)}/></label>
     <label>Kode permanen<input disabled={action==='edit'} required pattern="[a-z][a-z0-9_]*"
      maxLength={80} value={code} onChange={e=>setCode(e.target.value.toLowerCase())}/></label>
     <label>Urutan<input type="number" min={0} max={100000} value={order}
      onChange={e=>setOrder(Number(e.target.value))}/></label>
     <div className="org-buttons"><button className="btn primary" type="submit" disabled={busy}>Simpan</button>
      <button className="btn secondary" type="button" onClick={()=>setAction(null)}>Batal</button></div>
    </form>}
    {current&&!action&&<UnitAccess key={current.id} unit={current}/>}
   </div>
  </div>
 <CopySettings tree={tree} onDone={()=>{reload().catch(e=>setError(message(e)));setNotice("Pengaturan berhasil disalin. Atur ulang parameter utama.")}}/>
 </section>;
}
