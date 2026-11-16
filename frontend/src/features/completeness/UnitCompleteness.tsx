import {useEffect,useState} from 'react';
import {api,downloadApi,isoWita,qs} from '../../api';
import {basisLabel,cellLabel,coverageLabel,initialRange} from './completeness.mjs';
import type {DayCell,Summary} from './completeness.mjs';
import './completeness.css';

type Row={unit_id:number;unit_code:string;unit_name:string;level:string;depth:number;basis:'system.load'|'any_input';days:DayCell[];summary:Summary};
type Result={start:string;end:string;dates:string[];rows:Row[];summary:Summary};
const message=(e:unknown)=>e instanceof Error?e.message:String(e);
export default function UnitCompleteness({unitId,onOpen}:{unitId:number;onOpen:(unitId:number,day:string)=>void}){
 const [start,setStart]=useState(()=>initialRange(isoWita())[0]);
 const [end,setEnd]=useState(isoWita());
 const [result,setResult]=useState<Result|null>(null),[loading,setLoading]=useState(false),[error,setError]=useState('');
 const [revision,setRevision]=useState(0);
 const params=qs({start,end});
 useEffect(()=>{
  let alive=true;setLoading(true);setError('');setResult(null);
  api<Result>(`/org-units/${unitId}/completeness?${params}`)
   .then(data=>{if(alive)setResult(data)})
   .catch(e=>{if(alive)setError(message(e))})
   .finally(()=>{if(alive)setLoading(false)});
  return()=>{alive=false};
 },[unitId,params,revision]);
 async function exportFile(){
  try{setError('');await downloadApi(`/org-units/${unitId}/completeness/export?${params}`,
   `Kelengkapan_Unit_${start}_${end}.xlsx`)}catch(e){setError(message(e))}
 }
 return <section className="completeness-page">
  <div className="page-top"><div><div className="eyebrow">MONITORING · WITA</div>
   <h2>Kelengkapan Pengisian Unit</h2><p>Matriks jam tercatat per unit. D = draf, V = verified, F = final.</p></div></div>
  <div className="completeness-controls">
   <label>Mulai<input type="date" value={start} onChange={e=>setStart(e.target.value)}/></label>
   <label>Sampai<input type="date" value={end} onChange={e=>setEnd(e.target.value)}/></label>
   <button type="button" onClick={()=>setRevision(n=>n+1)}>Muat ulang</button>
   <button type="button" onClick={exportFile} disabled={!result}>Ekspor XLSX</button>
  </div>
  {error&&<div className="notice error" role="alert">{error}</div>}
  {loading&&<div className="loading">Memuat kelengkapan...</div>}
  {!loading&&result&&(!result.rows.length?<div className="notice">Belum ada ULP/KP aktif untuk ditampilkan.</div>:
   <div className="completeness-scroll"><table className="completeness-table">
    <thead><tr><th>Unit / Dasar</th>{result.dates.map(date=><th key={date}>{date.slice(5)}</th>)}
     <th>% Terisi</th><th>Hari final</th></tr></thead>
    <tbody>{result.rows.map(row=><tr key={row.unit_id}>
     <th><div style={{paddingLeft:`${row.depth*18}px`}}><strong>{row.unit_name}</strong>
      <small>{row.level.toUpperCase()} · {basisLabel(row.basis)}</small></div></th>
     {row.days.map(day=><td key={day.day}><button type="button"
      className={'completeness-cell '+day.status+(day.future?' future':'')}
      title={`${row.unit_name} · ${day.day} · ${day.status}`}
      onClick={()=>onOpen(row.unit_id,day.day)}>{cellLabel(day)}</button></td>)}
     <td>{coverageLabel(row.summary)}</td><td>{row.summary.final_days}</td>
    </tr>)}<tr className="completeness-total"><th>KESELURUHAN</th>
     <td colSpan={result.dates.length}>Jam terisi: {result.summary.filled_hours} / {result.summary.expected_hours}</td>
     <td>{coverageLabel(result.summary)}</td><td>{result.summary.final_days}</td>
    </tr></tbody></table></div>)}
  <p className="muted small">Sumber 0 dihitung terisi; NULL atau tanpa pembacaan tidak terisi.
   Jam yang sedang berjalan dihitung sejak awal jam WITA. Klik sel untuk melihat input unit pada tanggal tersebut.</p>
 </section>;
}
