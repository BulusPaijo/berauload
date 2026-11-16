import {useEffect,useState} from 'react';
import {api,type User} from '../../api';
import type {OrgUnit} from './OrgUnitManager';

const roles=['operator','verifier','management'];
type Grant={user_id:number;role:string};
const message=(e:unknown)=>e instanceof Error?e.message:String(e);

export default function UnitAccess({unit}:{unit:OrgUnit}){
 const [users,setUsers]=useState<User[]>([]);
 const [grants,setGrants]=useState<Grant[]>([]);
 const [error,setError]=useState('');
 const [success,setSuccess]=useState('');
 const [busy,setBusy]=useState(false);
 useEffect(()=>{
  let active=true;setError('');setSuccess('');
  Promise.all([api<User[]>('/users'),api<Grant[]>(`/org-units/${unit.id}/access`)])
   .then(([people,rows])=>{if(active){setUsers(people);setGrants(rows.filter(grant=>people.find(u=>u.id===grant.user_id)?.role!=='admin'))}})
   .catch(e=>{if(active)setError(message(e))});
  return()=>{active=false};
 },[unit.id]);
 const root=unit.level==='up3';
 function toggle(user:User,enabled:boolean){
  setGrants(current=>enabled?[...current.filter(r=>r.user_id!==user.id),
   {user_id:user.id,role:root?'management':user.role==='admin'?'management':user.role}]:current.filter(r=>r.user_id!==user.id));
 }
 async function save(){
  setBusy(true);setError('');setSuccess('');
  try{
   await api(`/org-units/${unit.id}/access`,{method:'PUT',
    body:JSON.stringify({entries:grants})});
   setSuccess('Akses unit berhasil disimpan. Hak unit sudah aktif.');
  }catch(e){setError(message(e))}finally{setBusy(false)}
 }
 return <section className="org-access">
  <h4>Akses Pengguna — {unit.name}</h4>
  <p className="muted small">Hak baca dan tulis mengikuti unit serta peran yang dipilih.</p>
  {root&&<p className="muted small">Pengguna UP3 non-admin hanya memiliki hak Management (baca).</p>}
  {error&&<div role="alert" className="notice error">{error}</div>}
  {success&&<div role="status" className="notice success">{success}</div>}
  <div className="org-access-table scroll-table"><table><thead><tr><th>Akses</th><th>Pengguna</th><th>Role pada unit</th></tr></thead><tbody>
  {users.filter(user=>user.role!=='admin').map(user=>{
   const item=grants.find(r=>r.user_id===user.id);
   return <tr key={user.id}><td><input aria-label={`Akses ${user.username}`} type="checkbox"
    checked={!!item} disabled={false} onChange={e=>toggle(user,e.target.checked)}/></td>
    <td>{user.name}<small className="muted"> · {user.username}</small></td>
    <td><select aria-label={`Role ${user.username}`} disabled={!item}
     value={item?.role||(root?'management':user.role)}
     onChange={e=>setGrants(current=>current.map(r=>r.user_id===user.id?{...r,role:e.target.value}:r))}>
     {(root?['management']:roles).map(role=><option key={role} value={role}>{role}</option>)}
     </select></td></tr>;
  })}
  </tbody></table></div>
  {<button className="btn primary" type="button" disabled={busy} onClick={save}>Simpan Akses</button>}
 </section>;
}
