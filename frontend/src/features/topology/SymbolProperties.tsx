import type {Asset} from '../../api';
import type {TopologySymbol,SymbolType,DiagramUnit} from './types';
import {SYMBOL_TYPES} from './stage4State.mjs';
type Props={symbol:TopologySymbol;assets:Asset[];onPatch:(patch:Partial<TopologySymbol>)=>void;onRemove:()=>void;targets:DiagramUnit[]};
export default function SymbolProperties({symbol:s,assets,onPatch,onRemove,targets}:Props){
 return <aside className="topo-properties" aria-label="Properti simbol">
  <h3>Properti Simbol</h3><span className="topo-editor-id">{s.id}</span>
  <label>Nama / label<input maxLength={120} value={s.label} onChange={e=>onPatch({label:e.target.value})}/></label>
  <label>Jenis simbol<select value={s.type} onChange={e=>onPatch({type:e.target.value as SymbolType})}>
   {SYMBOL_TYPES.map(type=><option key={type} value={type}>{type}</option>)}</select></label>
  <label>Peralatan (opsional)<select value={s.asset_code??''}
   onChange={e=>onPatch({asset_code:e.target.value||null})}>
   <option value="">Tanpa peralatan</option>
   {assets.filter(a=>a.active).map(a=><option key={a.id} value={a.code}>{a.name}</option>)}
  </select></label>
  <div className="topo-properties-grid">
   <label>X<input type="number" min={0} step={10} value={s.x}
    onChange={e=>onPatch({x:Number(e.target.value)})}/></label>
   <label>Y<input type="number" min={0} step={10} value={s.y}
    onChange={e=>onPatch({y:Number(e.target.value)})}/></label>
  </div>
  {s.type==='busbar'&&<label>Panjang busbar (px, kelipatan 10)
   <input type="number" min={40} max={1200} step={10} value={s.w}
    onChange={e=>{const n=Number(e.target.value);if(Number.isFinite(n))onPatch({w:n});}}/>
   <input type="range" min={40} max={1200} step={10} value={s.w}
    onChange={e=>onPatch({w:Number(e.target.value)})} aria-label="Atur panjang busbar"/>
   <small className="topo-faint">Panjang mengikuti grid; posisi dan garis penghubung lain tidak berubah otomatis.</small>
  </label>}
  <label>Rotasi<select value={s.rotation} onChange={e=>onPatch({rotation:Number(e.target.value) as 0|90|180|270})}>
   {[0,90,180,270].map(n=><option key={n} value={n}>{n}°</option>)}</select></label>
  <section className="topo-link-editor"><strong>Tautan ke diagram unit bawah</strong>
   <label>Unit tujuan<select value={s.link?.unit_id??''} onChange={e=>onPatch({link:e.target.value?{
    unit_id:Number(e.target.value),diagram_id:targets.find(u=>u.unit_id===Number(e.target.value))?.diagrams[0]?.id??0}:undefined})}>
    <option value="">Tidak ditautkan</option>{targets.filter(u=>u.diagrams.length).map(u=><option key={u.unit_id} value={u.unit_id}>{u.unit_name}</option>)}
   </select></label>
   {s.link&&<label>Diagram tujuan<select value={s.link.diagram_id||''} onChange={e=>onPatch({link:{unit_id:s.link!.unit_id,diagram_id:Number(e.target.value)}})}>
    <option value="">Pilih diagram</option>{targets.find(u=>u.unit_id===s.link?.unit_id)?.diagrams.map(d=><option key={d.id} value={d.id}>{d.name}</option>)}
   </select></label>}
   {s.link&&<button type="button" onClick={()=>onPatch({link:undefined})}>Hapus tautan</button>}
   <small className="topo-faint">Tautan hanya navigasi, bukan sambungan listrik.</small>
  </section>
  <p className="topo-faint">Simbol PMT selalu netral. Tidak ada fungsi buka/tutup dan tidak ada status switching.</p>
  <button type="button" className="topo-danger" onClick={onRemove}>Hapus Simbol</button>
 </aside>;
}
