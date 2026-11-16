import {useState} from 'react';
import type {User} from '../../../api';

type Conflict={kode:string;nilai_anda:number|null;nilai_server:number|null;
 diubah_oleh:string|null;waktu:string|null};
type Props={user:User;backup:{changedAt:number}|null;otherTab:boolean;
 sessionExpired:boolean;locked:boolean;error:string;
 conflicts:Record<number,Conflict[]>;restore:()=>void;discard:()=>void;
 resolve:(hour:number,code:string,useServer:boolean)=>void;
 login:(username:string,password:string)=>Promise<boolean>};
const display=(value:number|null)=>value===null?'Kosong':String(value);

export default function InputSaveFeedback(props:Props){
 const [password,setPassword]=useState('');
 const [busy,setBusy]=useState(false);
 return <>
  {props.backup&&<div className="notice warning" role="status">
   Ada isian belum tersimpan dari {new Date(props.backup.changedAt).toLocaleString('id-ID')}.
   <button className="btn secondary sm" onClick={props.restore}>Pulihkan</button>
   <button className="btn secondary sm" onClick={props.discard}>Buang</button>
  </div>}
  {props.otherTab&&<div className="notice warning">Hari yang sama dibuka pada tab lain. Periksa perubahan sebelum menyimpan.</div>}
  {props.locked&&<div className="notice error" role="alert">Hari terkunci di server. Simpan otomatis dihentikan. Isian tetap di cadangan lokal.</div>}
  {props.error&&<div className="notice error" role="alert">{props.error}</div>}
  {Object.entries(props.conflicts).filter(([,items])=>items.length).map(([hour,items])=><div key={hour} className="panel input-conflict">
   <h4>Konflik jam {String(hour).padStart(2,'0')}:00 — pilih untuk setiap parameter</h4>
   {items.map(item=><div className="conflict-item" key={item.kode}>
    <strong>{item.kode}</strong>
    <span>Nilai Anda: {display(item.nilai_anda)}</span>
    <span>Nilai server: {display(item.nilai_server)} ({item.diubah_oleh||'pengguna lain'}, {item.waktu||'waktu tidak diketahui'})</span>
    <button className="btn secondary sm" onClick={()=>props.resolve(Number(hour),item.kode,true)}>Pakai nilai server</button>
    <button className="btn primary sm" onClick={()=>props.resolve(Number(hour),item.kode,false)}>Timpa dengan nilai saya</button>
   </div>)}
  </div>)}
  {props.sessionExpired&&<div className="session-overlay" role="dialog" aria-modal="true" aria-label="Masuk kembali">
   <form className="panel session-dialog" onSubmit={async e=>{e.preventDefault();setBusy(true);
     if(await props.login(props.user.username,password))setPassword('');setBusy(false);}}>
    <h3>Sesi berakhir, masuk kembali</h3>
    <p>Isian belum tersimpan tetap ada. Masuk menggunakan akun yang sama untuk melanjutkan antrean.</p>
    <label>Username<input value={props.user.username} readOnly/></label>
    <label>Password<input type="password" value={password} required
       autoComplete="current-password" onChange={e=>setPassword(e.target.value)}/></label>
    <button className="btn primary" disabled={busy}>{busy?'Memverifikasi...':'Masuk kembali'}</button>
   </form>
  </div>}
 </>;
}
