import {useEffect, useState, type FormEvent} from 'react';
import {api, type Role} from '../../api';
import {flattenUnits, type UnitNode} from '../org-units/unitSelection.mjs';
import {initialGrant, summarizeUserAccess, validateAccess, type UserGrant, type AccessRow, type UnitRole} from './userAccess.mjs';
import './users.css';

type UserRow = {id:number; username:string; name:string; role:Role; active:boolean};
type NewUser = {username:string; display_name:string; password:string; role:Role};
const emptyForm: NewUser = {username:'', display_name:'', password:'', role:'operator'};
const roles: UnitRole[] = ['operator', 'verifier', 'management'];
const roleLabels: Record<UnitRole, string> = {operator:'Operator', verifier:'Verifier', management:'Manajemen'};
const messageOf = (error:unknown) => error instanceof Error ? error.message : String(error);

export default function UserManager(){
  const [users,setUsers] = useState<UserRow[]>([]);
  const [units,setUnits] = useState<UnitNode[]>([]);
  const [allGrants,setAllGrants] = useState<AccessRow[]>([]);
  const [form,setForm] = useState<NewUser>(emptyForm);
  const [grants,setGrants] = useState<UserGrant[]>([]);
  const [error,setError] = useState('');
  const [formError,setFormError] = useState('');
  const [success,setSuccess] = useState('');
  const [busy,setBusy] = useState(false);
  const [loading,setLoading] = useState(true);
  const [revision,setRevision] = useState(0);

  useEffect(()=>{
    let active = true;
    setLoading(true);
    Promise.all([api<UserRow[]>('/users'),api<UnitNode[]>('/org-units')])
      .then(async ([people,tree])=>{
        const allUnits = flattenUnits(tree);
        const accesses = await Promise.all(allUnits.map(unit=>
          api<AccessRow[]>(`/org-units/${unit.id}/access`)));
        if(active){setUsers(people);setUnits(allUnits);setAllGrants(accesses.flat());setError('');}
      })
      .catch(e=>{if(active)setError(messageOf(e));})
      .finally(()=>{if(active)setLoading(false);});
    return ()=>{active=false;};
  },[revision]);

  const unitNames = new Map(units.map(unit=>[unit.id,unit.name]));
  function toggleUnit(unit:UnitNode,checked:boolean){
    setGrants(current=>checked
      ? [...current.filter(g=>g.unit_id!==unit.id),initialGrant(unit,form.role==='admin'?'operator':form.role)]
      : current.filter(g=>g.unit_id!==unit.id));
    setFormError('');
  }
  function changeRole(unit:UnitNode,role:UnitRole){
    setGrants(current=>current.map(grant=>grant.unit_id===unit.id
      ? {...grant,role:unit.level==='up3'?'management':role}:grant));
  }
  async function createUser(event:FormEvent){
    event.preventDefault();setSuccess('');setError('');
    const problem = validateAccess(form.role,grants);
    if(problem){setFormError(problem);return;}
    setFormError('');setBusy(true);
    try{
      await api('/users',{method:'POST',body:JSON.stringify({...form,accesses:form.role==='admin'?[]:grants})});
      setForm(emptyForm);setGrants([]);setSuccess('Pengguna berhasil dibuat.');
      setRevision(n=>n+1);
    }catch(e){setError(messageOf(e));}finally{setBusy(false);}
  }
  async function toggleUser(user:UserRow){
    if(!window.confirm(`${user.active?'Nonaktifkan':'Aktifkan'} akun ${user.username}?`))return;
    try{
      await api(`/users/${user.id}/active`,{method:'PUT',body:JSON.stringify({active:!user.active})});
      setError('');setRevision(n=>n+1);
    }catch(e){setError(messageOf(e));}
  }
  async function resetUser(user:UserRow){
    const password = window.prompt(`Password baru untuk ${user.username} (minimal 16 karakter)`);
    if(!password)return;
    try{
      await api(`/users/${user.id}/reset-password`,{method:'POST',body:JSON.stringify({password})});
      setSuccess('Password berhasil di-reset dan sesi lama telah dicabut.');setError('');
    }catch(e){setError(messageOf(e));}
  }

  return <div className="user-manager page-space">
    {error&&<div className="notice error" role="alert">{error}</div>}
    {success&&<div className="notice success" role="status">{success}</div>}
    <section className="panel"><div className="panel-head"><h3>Buat Pengguna Baru</h3></div>
      <form className="user-manager-form" onSubmit={createUser}>
        <div className="user-identity">
          <div className="field"><label htmlFor="new-username">Username</label><input id="new-username" value={form.username} onChange={e=>setForm({...form,username:e.target.value})} required/></div>
          <div className="field"><label htmlFor="new-display-name">Nama</label><input id="new-display-name" value={form.display_name} onChange={e=>setForm({...form,display_name:e.target.value})} required/></div>
          <div className="field"><label htmlFor="new-password">Password (≥16 karakter)</label><input id="new-password" type="password" value={form.password} minLength={16} onChange={e=>setForm({...form,password:e.target.value})} required/></div>
        </div>
        <fieldset className="user-account-section"><legend>Jenis akun</legend>
          <div className="field"><label htmlFor="account-role">Role</label><select id="account-role" value={form.role} onChange={e=>{setForm({...form,role:e.target.value as Role});setFormError('');}}>
            <option value="operator">Operator</option><option value="verifier">Verifier</option>
            <option value="management">Manajemen</option><option value="admin">Admin</option>
          </select></div>
          {form.role==='admin'&&<p className="user-account-note">Admin berlaku untuk semua unit.</p>}
        </fieldset>
        {form.role!=='admin'&&<fieldset className="user-account-section"><legend>Akses unit</legend>
          <p className="muted small">Centang unit yang diizinkan, lalu pilih peran pada masing-masing unit.</p>
          <div className="user-grant-list">{units.filter(unit=>unit.active).map(unit=>{
            const grant=grants.find(item=>item.unit_id===unit.id);
            return <div className="user-grant-row" key={unit.id}>
              <label className="user-unit-checkbox" htmlFor={`user-unit-${unit.id}`}>
                <input id={`user-unit-${unit.id}`} type="checkbox" checked={!!grant} onChange={e=>toggleUnit(unit,e.target.checked)}/>
                <span>{unit.name}</span><small>{unit.level.toUpperCase()}</small>
              </label>
              {grant&&<div className="field user-unit-role">
                <label htmlFor={`user-role-${unit.id}`}>Peran di {unit.name}</label>
                <select id={`user-role-${unit.id}`} value={grant.role} onChange={e=>changeRole(unit,e.target.value as UnitRole)}>
                  {(unit.level==='up3'?(['management'] as UnitRole[]):roles).map(role=><option key={role} value={role}>{roleLabels[role]}</option>)}
                </select>
              </div>}
            </div>;
          })}</div>
          {!loading&&!units.some(unit=>unit.active)&&<p className="muted small">Belum ada unit aktif yang bisa diberikan akses.</p>}
          {formError&&<p role="alert" className="user-grant-error">{formError}</p>}
        </fieldset>}
        <div><button className="btn primary" disabled={busy||loading}>{busy?'Menyimpan...':'Tambah Pengguna'}</button></div>
      </form>
    </section>
    <section className="panel"><div className="panel-head"><h3>Daftar Pengguna</h3></div>
      {loading?<div className="muted small">Memuat pengguna dan akses unit...</div>:<div className="scroll-table"><table>
        <thead><tr><th>Username</th><th>Nama</th><th>Role</th><th>Akses unit</th><th>Aktif</th><th>Aksi</th></tr></thead>
        <tbody>{users.map(user=><tr key={user.id}>
          <td>{user.username}</td><td>{user.name}</td><td>{user.role}</td>
          <td className="user-access-summary">{summarizeUserAccess(user,allGrants,unitNames)}</td>
          <td>{user.active?'Ya':'Tidak'}</td>
          <td><button className="link-btn" onClick={()=>resetUser(user)}>Reset Password</button>
            <button className="link-btn danger-text" onClick={()=>toggleUser(user)}>{user.active?'Nonaktifkan':'Aktifkan'}</button></td>
        </tr>)}</tbody>
      </table></div>}
    </section>
  </div>;
}
