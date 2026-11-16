import type {UnitNode} from './unitSelection.mjs';
import {flattenUnits} from './unitSelection.mjs';
export default function UnitSelector({tree,value,onSelect}:{tree:UnitNode[];value:number|null;onSelect:(id:number)=>void}){
 return <div className="unit-selector"><label htmlFor="active-unit">Unit aktif</label>
 <select id="active-unit" value={value??''} onChange={e=>onSelect(Number(e.target.value))}>
 {flattenUnits(tree).filter(u=>u.active).map(u=><option value={u.id} key={u.id}>
 {u.level==='up3'?'UP3':u.level==='ulp'?'　ULP':'　　KP'} · {u.name}</option>)}
 </select></div>;
}
