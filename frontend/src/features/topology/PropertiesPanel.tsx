/** Admin properties: data-source references only; never edits electrical values. */
import {useState} from 'react';
import type {Asset,Metric} from '../../api';
import type {TopologyBox,TopologyLayout,TopologyRule} from './types';
import {validEditorMetric} from './editorState.mjs';

type Props={box:TopologyBox|null;layout:TopologyLayout;assets:Asset[];metrics:Metric[];
 rules:TopologyRule[];onPatch:(patch:Partial<TopologyBox>)=>void;
 onRebind:(assetCode:string|null)=>void;onMove:(x:number,y:number)=>void;
 onDuplicate:()=>void;onDelete:()=>void;onApplyKind:()=>void};
const numeric=(value:string,fallback:number)=>Number.isFinite(Number(value))?Number(value):fallback;

export default function PropertiesPanel(p:Props){
 const [search,setSearch]=useState('');
 const b=p.box;
 if(!b)return <aside className="topo-properties"><h3>Properti Kotak</h3>
  <p className="topo-faint">Pilih kotak pada kanvas atau tambah kotak parameter baru.</p>
  <p className="topo-faint">Hubungan listrik belum digambar otomatis.</p></aside>;
 const available=p.metrics.filter(m=>validEditorMetric(m,b.asset_code,p.assets));
 const selected=new Set(b.metric_codes);
 const referenceUnit=p.metrics.find(m=>m.code===b.metric_codes[0])?.unit;
 const compatible=available.filter(m=>b.kind!=='ranking'||!referenceUnit||m.unit===referenceUnit);
 const shown=compatible.filter(m=>`${m.name} ${m.code}`.toLocaleLowerCase('id').includes(search.trim().toLocaleLowerCase('id')));
 const changeMetric=(code:string,checked:boolean)=>{
  if(checked&&b.metric_codes.length>=6)return;
  p.onPatch({metric_codes:checked?[...b.metric_codes,code]:b.metric_codes.filter(x=>x!==code)});
 };
 const moveMetric=(index:number,delta:number)=>{
  const dest=index+delta;if(dest<0||dest>=b.metric_codes.length)return;
  const codes=[...b.metric_codes];[codes[index],codes[dest]]=[codes[dest],codes[index]];
  p.onPatch({metric_codes:codes});
 };
 return <aside className="topo-properties" aria-label="Properti kotak parameter">
  <h3>Properti Kotak</h3><span className="topo-editor-id">{b.id}</span>
  <label>Judul kotak<input value={b.title} maxLength={120} onChange={e=>p.onPatch({title:e.target.value})}/></label>
  <label>Peralatan<select value={b.asset_code??''} onChange={e=>p.onRebind(e.target.value||null)}>
   <option value="">Semua parameter aktif</option>
   {p.assets.filter(a=>a.active).map(a=><option key={a.id} value={a.code}>{a.name}</option>)}
  </select></label>
  {['metric','summary','ranking'].includes(b.kind)&&<div className="topo-property-heading">Parameter terpilih ({b.metric_codes.length}/6)</div>}
  {['metric','summary','ranking'].includes(b.kind)&&<div className="topo-selected-metrics">{b.metric_codes.map((code,i)=><div key={code}>
   <span title={code}>{p.metrics.find(m=>m.code===code)?.name??code}</span>
   <button type="button" aria-label={`Naikkan ${code}`} disabled={i===0} onClick={()=>moveMetric(i,-1)}>↑</button>
   <button type="button" aria-label={`Turunkan ${code}`} disabled={i===b.metric_codes.length-1} onClick={()=>moveMetric(i,1)}>↓</button>
  </div>)}</div>}
  {['metric','summary','ranking'].includes(b.kind)&&<label className="topo-param-search">Cari parameter
   <input type="search" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Cari nama atau kode parameter..."/>
  </label>}
  {['metric','summary','ranking'].includes(b.kind)&&<div className="topo-metric-options" role="group" aria-label="Pilih parameter">
   {shown.map(m=><label key={m.code} className="topo-check-row">
    <input type="checkbox" checked={selected.has(m.code)}
     disabled={!selected.has(m.code)&&selected.size>=6||selected.has(m.code)&&selected.size===1}
     onChange={e=>changeMetric(m.code,e.target.checked)}/>
    <span>{m.name} <small>({m.unit})</small></span>
   </label>)}
   {!shown.length&&<p className="topo-faint">{search?'Tidak ada parameter yang cocok.':'Tidak ada parameter aktif dengan satuan kompatibel.'}</p>}
  </div>}
  {['metric','summary','ranking'].includes(b.kind)&&!b.metric_codes.length&&<p className="topo-input-warning">Pilih minimal satu parameter sebelum menyimpan.</p>}
  <div className="topo-properties-grid">
   <label>X<input type="number" step={10} min={0} value={b.x} disabled={b.locked}
    onChange={e=>p.onMove(numeric(e.target.value,b.x),b.y)}/></label>
   <label>Y<input type="number" step={10} min={0} value={b.y} disabled={b.locked}
    onChange={e=>p.onMove(b.x,numeric(e.target.value,b.y))}/></label>
   <label>Lebar<input type="number" min={160} max={500} step={10} value={b.w}
    onChange={e=>p.onPatch({w:Math.max(160,Math.min(500,Math.round(numeric(e.target.value,b.w)/10)*10))})}/></label>
   <label>Desimal<select value={b.decimals} onChange={e=>p.onPatch({decimals:Number(e.target.value)})}>
    {[0,1,2,3,4].map(n=><option key={n} value={n}>{n}</option>)}
   </select></label>
  </div>
  {b.kind!=='text'&&b.kind!=='legend'&&<label>Rule status aktif<select value={b.rule_id??''}
   onChange={e=>p.onPatch({rule_id:e.target.value?Number(e.target.value):null})}>
   <option value="">Tidak ada rule</option>
   {p.rules.filter(r=>r.status==='active').map(r=><option key={r.id} value={r.id}>{r.name}</option>)}
  </select></label>}
  <label>Simbol jangkar<select value={b.anchor_symbol_id??''} onChange={e=>p.onPatch({
   anchor_symbol_id:e.target.value||null,leader:Boolean(e.target.value)&&b.leader})}>
   <option value="">Tidak ada jangkar</option>
   {p.layout.symbols.map(s=><option key={s.id} value={s.id}>{s.label}</option>)}
  </select></label>
  <div className="topo-property-flags">
   {([['show_unit','Tampilkan satuan'],['leader','Garis ke simbol jangkar'],
    ['sparkline','Grafik mini 24 jam'],['locked','Kunci posisi']] as const).filter(([key])=>
     (key!=='sparkline'&&key!=='show_unit')||['metric','summary','ranking'].includes(b.kind)).map(([key,label])=><label key={key} className="topo-check-row">
    <input type="checkbox" checked={b[key]} disabled={key==='leader'&&!b.anchor_symbol_id}
     onChange={e=>p.onPatch({[key]:e.target.checked} as Partial<TopologyBox>)}/>{label}
   </label>)}
  </div>
  <div className="topo-editor-actions stack">
   <button type="button" onClick={p.onDuplicate}>Duplikat Kotak</button>
   <button type="button" onClick={p.onApplyKind} disabled={!b.asset_code}>Terapkan susunan ke peralatan sejenis</button>
   <button type="button" className="topo-danger" onClick={p.onDelete}>Hapus Kotak</button>
  </div>
  <p className="topo-faint">Perubahan hanya pada konfigurasi. Nilai pengukuran tidak dapat diubah di halaman ini.</p>
 </aside>;
}
