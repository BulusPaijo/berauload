/** Explicit palette: visual placement never establishes electrical connectivity. */
import type {SymbolType,BoxKind} from './types';
import type {Asset,Metric} from '../../api';
import type {ReactNode} from 'react';
import {SYMBOL_TYPES} from './stage4State.mjs';
export type EditorTool={kind:'select'|'symbol'|'wire'|'area';symbolType?:SymbolType};
const LABELS:Record<SymbolType,string>={
 generator:'Pembangkit',incoming:'Incoming',busbar:'Busbar',breaker:'PMT (netral)',
 transformer:'Transformator',feeder:'Penyulang',load:'Beban',capacitor:'Kapasitor'};
const BOX_LABELS:Record<BoxKind,string>={metric:'Parameter',summary:'Ringkasan',
 ranking:'Peringkat',legend:'Legenda',text:'Teks'};
type Props={tool:EditorTool;onTool:(tool:EditorTool)=>void;
 onAddBox:(kind:BoxKind)=>void;canAddBox:boolean;onAssetDraft:()=>void;
 assets:Asset[];metrics:Metric[];assetCode:string;metricCode:string;
 onAssetCode:(code:string)=>void;onMetricCode:(code:string)=>void;
 name:string;description:string;onName:(text:string)=>void;onDescription:(text:string)=>void;
 revisions:{version:number}[];onRestore:(version:number)=>void;activeVersion:number;saving:boolean;canvasSettings:ReactNode};
export default function Palette(p:Props){
 return <aside className="topo-palette" aria-label="Palet builder topologi">
  <h3>Palet Builder</h3>
  <label>Nama diagram<input maxLength={150} value={p.name} onChange={e=>p.onName(e.target.value)}/></label>
  <label>Deskripsi<textarea maxLength={500} rows={2} value={p.description}
    onChange={e=>p.onDescription(e.target.value)}/></label>
  {p.canvasSettings}
  <div className="topo-property-heading">Alat Gambar</div>
  <div className="topo-palette-grid">
   <button type="button" className={p.tool.kind==='select'?'is-active':''}
    aria-pressed={p.tool.kind==='select'} onClick={()=>p.onTool({kind:'select'})}>↖ Pilih / Geser</button>
   <button type="button" className={p.tool.kind==='area'?'is-active':''}
    aria-pressed={p.tool.kind==='area'} onClick={()=>p.onTool({kind:'area'})}>▣ Area / Kelompok</button>
   <button type="button" className={p.tool.kind==='wire'?'is-active':''}
    aria-pressed={p.tool.kind==='wire'} onClick={()=>p.onTool({kind:'wire'})}>╱ Gambar Garis</button>
  </div>
  <p className="topo-faint">Area untuk menandai GI, GH, atau pembangkit; tidak menghubungkan peralatan.</p>
  <div className="topo-property-heading">Simbol Kelistrikan</div>
  <div className="topo-palette-grid">
   {SYMBOL_TYPES.map(type=><button key={type} type="button" draggable
    className={p.tool.kind==='symbol'&&p.tool.symbolType===type?'is-active':''}
    aria-pressed={p.tool.kind==='symbol'&&p.tool.symbolType===type}
    onClick={()=>p.onTool({kind:'symbol',symbolType:type})}
    onDragStart={e=>e.dataTransfer.setData('application/x-berauload-symbol',type)}>
     {LABELS[type]}
   </button>)}
  </div>
  <p className="topo-faint">Klik simbol lalu klik kanvas, atau seret simbol ke kanvas. Posisi dapat digeser setelah ditambahkan.</p>
  <div className="topo-property-heading">Sumber Kotak</div>
  <label>Peralatan<select value={p.assetCode} onChange={e=>p.onAssetCode(e.target.value)}>
   <option value="">Semua peralatan</option>
   {p.assets.filter(a=>a.active).map(a=><option key={a.id} value={a.code}>{a.name}</option>)}
  </select></label>
  <label>Parameter awal<select value={p.metricCode} onChange={e=>p.onMetricCode(e.target.value)}>
   {p.metrics.length?p.metrics.map(m=><option key={m.id} value={m.code}>{m.name} ({m.unit})</option>):
    <option value="">Tidak tersedia</option>}
  </select></label>
  <div className="topo-property-heading">Kotak Informasi</div>
  <div className="topo-palette-grid">
   {(Object.keys(BOX_LABELS) as BoxKind[]).map(kind=><button key={kind} type="button"
    disabled={!p.canAddBox&&['metric','summary','ranking'].includes(kind)}
    onClick={()=>p.onAddBox(kind)}>{BOX_LABELS[kind]}</button>)}
  </div>
  <p className="topo-faint">Pilih parameter pada panel kanan. Kotak peringkat hanya membandingkan satuan yang sama.</p>
  <div className="topo-property-heading">Draf Peralatan</div>
  <button type="button" onClick={p.onAssetDraft}>Buat draf dari daftar peralatan</button>
  <p className="topo-faint">Hanya menata simbol; tidak membuat koneksi listrik.</p>
  <div className="topo-property-heading">Riwayat Revisi</div>
  <div className="topo-revision-list">{p.revisions.map(rev=><button key={rev.version} type="button"
   onClick={()=>p.onRestore(rev.version)} disabled={p.saving||rev.version===p.activeVersion}>
   Revisi {rev.version} <small>· Pulihkan</small></button>)}</div>
 </aside>;
}
