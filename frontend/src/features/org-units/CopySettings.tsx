import {useState} from 'react';
import {api} from '../../api';
import type {OrgUnit} from './OrgUnitManager';
import {flattenUnits} from './unitSelection.mjs';
type Preview={assets:Record<string,string>;metrics:Record<string,string>;tabs:Record<string,string>;counts:Record<string,number>;will_copy_readings:boolean;will_copy_day_states:boolean};
export default function CopySettings({tree,onDone}:{tree:OrgUnit[];onDone:()=>void}){
 const units=flattenUnits(tree).filter(x=>x.active&&x.level!=='up3');
 const [source,setSource]=useState(0),[target,setTarget]=useState(0),[topology,setTopology]=useState(false);
 const [plan,setPlan]=useState<Preview|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 async function call(action:'preview'|'commit'){
  setBusy(true);setError('');if(action==='preview')setPlan(null);
  try{if(!source||!target||source===target)throw new Error('Pilih dua unit berbeda.');
   if(action==='commit'&&!window.confirm('Salin konfigurasi ke unit kosong? Pembacaan dan status hari tidak disalin.'))return;
   const response=await api<Preview>(`/org-units/${target}/copy-settings/${action}`,{method:'POST',body:JSON.stringify({source_unit_id:source,include_topology:topology})});
   if(action==='preview')setPlan(response);else{setPlan(null);onDone();}
  }catch(e){setError(e instanceof Error?e.message:String(e))}finally{setBusy(false)}
 }
 return <section className="panel"><h3>Salin Pengaturan Unit</h3><p>Hanya untuk unit tujuan kosong. Parameter computed tanpa formula, termasuk rekap beban sistem dan daya mampu, tidak disalin. Parameter utama wajib diatur ulang. Pembacaan dan status hari tidak disalin.</p>
 <div className="toolbar-actions"><label>Sumber <select value={source} onChange={e=>{setSource(Number(e.target.value));setPlan(null)}}><option value={0}>Pilih unit</option>{units.map(u=><option key={u.id} value={u.id}>{u.name}</option>)}</select></label>
 <label>Tujuan (kosong) <select value={target} onChange={e=>{setTarget(Number(e.target.value));setPlan(null)}}><option value={0}>Pilih unit</option>{units.map(u=><option key={u.id} value={u.id}>{u.name}</option>)}</select></label>
 <label><input type="checkbox" checked={topology} onChange={e=>{setTopology(e.target.checked);setPlan(null)}}/> Sertakan topologi</label><button className="btn secondary" disabled={busy} onClick={()=>call('preview')}>Pratinjau</button></div>
 {error&&<p role="alert" className="notice error">{error}</p>}
 {plan&&<><h4>Pratinjau (baca-saja)</h4><p>{Object.entries(plan.counts).map(([key,val])=>`${key}: ${val}`).join(' · ')}</p>
 {(['assets','metrics','tabs'] as const).map(group=><div key={group}><strong>{group}</strong><div className="scroll-table"><table><thead><tr><th>Kode lama</th><th>Kode baru</th></tr></thead><tbody>{Object.entries(plan[group]).map(([oldCode,newCode])=><tr key={oldCode}><td>{oldCode}</td><td>{newCode}</td></tr>)}</tbody></table></div></div>)}
 <button disabled={busy} className="btn primary" onClick={()=>call('commit')}>Konfirmasi Salin Pengaturan</button></>}
 </section>;
}
