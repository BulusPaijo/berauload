import {displayValue} from './helpers.mjs';
import type {CalcResults} from './types';
export default function ResultPanel({data}:{data:CalcResults|null}){
 if(!data)return null;
 return <div className="calc-readonly">
  <h4>Hasil hitung & temuan {data.stale&&<span className="calc-warning">Versi lama — menunggu hitung ulang</span>}</h4>
  {data.columns.length?<div className="calc-readonly-grid">{data.columns.map(col=><div key={col.code}>
   <span>{col.name}</span><strong>{displayValue(col.value,col.decimals,col.incomplete)} {col.value!==null&&col.unit}</strong>
   {col.note&&<small>{col.note}</small>}</div>)}</div>:<p>Belum ada hasil hitung untuk pengukuran ini.</p>}
  <div className="calc-tags">{data.matches.map(rule=><span key={rule.code} className="calc-tag"
   style={{borderColor:rule.color}}>{rule.name}</span>)}
   {!data.matches.some(r=>r.kind==='category')&&<span className="calc-tag">Tidak dapat dinilai</span>}
  </div>
 </div>;
}
