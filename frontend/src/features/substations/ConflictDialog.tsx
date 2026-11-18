import {conflictCells} from './conflict.mjs';
import type {Def,Visit} from './types';

type Props={id:number;server:Visit & {updated_by_name?:string|null};drafts:Record<string,string>;
 params:Def[];onReload:()=>void;onKeep:()=>void};
const text=(raw:string)=>raw===''?'Kosong':raw.startsWith('@')?`Flag ${raw.slice(1)}`:raw;
export default function ConflictDialog({id,server,drafts,params,onReload,onKeep}:Props){
 const rows=conflictCells(drafts,id,server.values||[],params);
 return <div className="substation-dialog" role="dialog" aria-label={`Konflik pengukuran gardu ${id}`}>
  <div className="substation-dialog-head"><div><span className="substation-kicker">PERUBAHAN BERSAMA</span><h3>Konflik penyimpanan gardu #{id}</h3></div><span className="substation-chip danger">Perlu keputusan</span></div>
  <p>Data di server telah berubah. Ketikan Anda tidak akan ditimpa atau dikirim tanpa keputusan Anda.</p>
  <div className="substation-conflict-meta"><span>Diubah oleh: <strong>{server.updated_by_name||`Pengguna #${server.updated_by??'—'}`}</strong></span><span>Waktu: <strong>{server.updated_at?new Date(server.updated_at).toLocaleString('id-ID'):'—'}</strong></span><span>Status: <strong>{server.state}</strong></span></div>
  <div className="scroll-table"><table><thead><tr><th>Parameter</th><th>Jurusan</th><th>Nilai Anda</th><th>Nilai server</th></tr></thead><tbody>{rows.map(row=><tr key={row.key}><td>{row.label}</td><td>{row.line||'Gardu'}</td><td>{text(row.mine)}</td><td>{text(row.server)}</td></tr>)}
   {!rows.length&&<tr><td colSpan={4}>Tidak ada sel yang berbeda. Perbarui data untuk melanjutkan.</td></tr>}</tbody></table></div>
  <div className="substation-dialog-actions"><button className="btn secondary" onClick={onReload}>Muat ulang data server</button><button className="btn primary" onClick={onKeep}>Pertahankan ketikan saya (salin setelah muat ulang)</button></div>
 </div>;
}
