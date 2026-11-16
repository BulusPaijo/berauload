import {unitMetricGroups} from '../unit-references/UnitMetricOptions';
import {useEffect,useMemo,useState} from 'react';
import {api} from '../../api';
import {useUnitMetricReferences,metricsForSelection} from '../unit-references/useUnitMetricReferences';
import type {UnitItem} from '../units/UnitManager';
import {Save,X} from 'lucide-react';
import type {Catalog} from '../../api';
import type {DashPanel,PanelKind,PanelSource,HistoricalOption,RuleOption} from './types';


type Props={initial:DashPanel;catalog:Catalog;historical:HistoricalOption[];rules:RuleOption[];
 onSave:(panel:DashPanel)=>void;onClose:()=>void};
const TYPES:[PanelKind,string][]=[['line','Grafik Garis'],['area','Grafik Area'],['bar','Grafik Batang'],
 ['step','Grafik Tangga'],['stacked_bar','Batang Bertumpuk'],['stat','Kartu KPI'],['gauge','Gauge'],['table','Tabel'],['rule','Status Engineering']];

export default function PanelEditor({initial,catalog,historical,rules,onSave,onClose}:Props){
  const [panel,setPanel]=useState<DashPanel>({...initial});
  const CAP=catalog.roles?.['system.capacity']||'';
  const LOAD=catalog.roles?.['system.load']||'';
  const [units,setUnits]=useState<UnitItem[]>([]);
  useEffect(()=>{api<UnitItem[]>('/units').then(setUnits).catch(()=>{});},[]);
  const [error,setError]=useState('');
  const referenceMetrics=useUnitMetricReferences();
  const options=useMemo(()=>metricsForSelection(referenceMetrics,catalog.metrics).filter(m=>m.active&&m.code!=='daya_mampu_sistem_kw'),[catalog,referenceMetrics]);
  const isPaired=Boolean(CAP&&LOAD&&panel.metric_codes.includes(CAP)&&panel.metric_codes.includes(LOAD));
  const activeSource=panel.source;
  const sourceUnit=options.find(m=>m.code===panel.metric_codes[0])?.unit;
  const sourceDim=units.find(u=>u.code===sourceUnit)?.dimension;
  const compatible=units.filter(u=>u.active&&sourceDim&&u.dimension===sourceDim);
  const seriesToColor=panel.source==='metric'?options.filter(m=>panel.metric_codes.includes(m.code)).map(m=>({code:m.code,name:m.name})):
    panel.source==='historical'?[{code:'value',name:panel.title}]:[];
  function patch(change:Partial<DashPanel>){setPanel(p=>({...p,...change}));setError('')}
  function changeSource(source:PanelSource){
    patch({source,kind:source==='engineering'?'rule':source==='historical'?'stat':'line',
      metric_codes:source==='metric'&&LOAD?[LOAD]:[],source_id:source==='historical'?historical[0]?.id||null:source==='engineering'?rules.find(r=>r.status==='active')?.id||null:null,
      aggregation:'avg',display_unit:null,colors:{}});
  }
  function toggleMetric(code:string){
    const isSelected=panel.metric_codes.includes(code);
    const base=panel.metric_codes.filter(c=>c!==code);
    const unit=options.find(m=>m.code===code)?.unit;
    const compatibleForAll=base.every(c=>{
      const other=options.find(m=>m.code===c)?.unit;
      return other===unit||!!(panel.display_unit&&units.find(u=>u.code===other)?.dimension===
        units.find(u=>u.code===unit)?.dimension);
    });
    if(!isSelected&&(base.length>=4||!compatibleForAll)){
      setError('Maksimal 4 parameter dalam satu panel, dengan satuan yang sama.');return;
    }
    patch({metric_codes:isSelected?base:[...base,code],display_unit:compatibleForAll?panel.display_unit:null,colors:{},aggregation:!isSelected&&CAP&&LOAD&&[...base,code].includes(CAP)&&[...base,code].includes(LOAD)?'avg':panel.aggregation});
  }
  function submit(event:React.FormEvent){
    event.preventDefault();
    if(panel.source==='metric'&&(!panel.metric_codes.length||(['stat','gauge'].includes(panel.kind)&&panel.metric_codes.length!==1))){
      setError('Pilih parameter sesuai jenis panel (KPI/Gauge: satu parameter).');return;
    }
    if(isPaired&&(panel.metric_codes.length!==2||panel.aggregation!=='avg'||panel.kind==='stacked_bar')){
      setError('Perbandingan H/J hanya boleh memakai dua parameter dan rata-rata berpasangan.');return;
    }
    if(panel.source!=='metric'&&!panel.source_id){setError('Pilih formula historis / rule aktif.');return;}
    onSave(panel);
  }
  return <div className="dash-drawer-shade" onMouseDown={e=>{if(e.target===e.currentTarget)onClose()}}>
    <aside className="dash-drawer" role="dialog" aria-modal="true" aria-label="Editor panel dashboard">
      <header><div><h3>{initial.title?'Edit Panel':'Tambah Panel'}</h3><p>Pilih sumber data dan jenis tampilan.</p></div>
        <button type="button" className="dash-icon" title="Tutup editor" onClick={onClose}><X size={20}/></button></header>
      <form onSubmit={submit} className="dash-editor-form">
        <label>Nama Panel <input required minLength={2} maxLength={120} value={panel.title} onChange={e=>patch({title:e.target.value})}/></label>
        <label>Sumber Data<select value={activeSource} onChange={e=>changeSource(e.target.value as PanelSource)}>
          <option value="metric">Parameter Pengukuran / Computed</option><option value="historical">Perhitungan Historis V1.2</option>
          <option value="engineering">Engineering Rules V1.3</option></select></label>
        <label>Jenis Visualisasi<select value={panel.kind} onChange={e=>patch({kind:e.target.value as PanelKind,metric_codes:['stat','gauge'].includes(e.target.value)?panel.metric_codes.slice(0,1):panel.metric_codes})}>
          {TYPES.filter(([type])=>activeSource==='engineering'?type==='rule':activeSource==='historical'?['line','area','bar','step','stat','table'].includes(type):type!=='rule').map(([value,label])=><option key={value} value={value}>{label}</option>)}
        </select></label>
        {activeSource==='metric'&&<div className="dash-metric-editor"><strong>Parameter pada panel</strong>
          <p>Pastikan satuan sama. Untuk pasangan kolom H/J, gunakan agregasi rata-rata.</p>
          {unitMetricGroups(options).map(group=><fieldset key={group.name} className="dash-unit-group"><legend>{group.name}</legend>
            {group.items.map(m=><label key={m.code} className="dash-metric-row"><input type="checkbox" checked={panel.metric_codes.includes(m.code)}
            onChange={()=>toggleMetric(m.code)}/><span>{'label' in m ? String(m.label) : m.name}<small>{m.code} · {m.unit}</small></span></label>)}
          </fieldset>)}
          <button type="button" disabled={!CAP||!LOAD} className="btn secondary sm" onClick={()=>patch({metric_codes:[CAP,LOAD],aggregation:'avg',kind:'line',title:'Daya Mampu vs Beban Sistem'})}>Pakai Grafik Standar H/J</button>
        </div>}
        {activeSource==='historical'&&<label>Formula Historis<select value={panel.source_id||''} onChange={e=>patch({source_id:Number(e.target.value)})}>
          <option value="">Pilih formula</option>{historical.filter(h=>!h.archived).map(h=><option key={h.id} value={h.id}>{h.name} ({h.unit})</option>)}
        </select></label>}
        {activeSource==='engineering'&&<label>Engineering Rule<select value={panel.source_id||''} onChange={e=>patch({source_id:Number(e.target.value)})}>
          <option value="">Pilih rule aktif</option>{rules.filter(r=>r.status==='active').map(r=><option key={r.id} value={r.id}>{r.name}</option>)}
        </select></label>}
        {activeSource==='metric'&&<label>Agregasi<select value={panel.aggregation} disabled={isPaired} onChange={e=>patch({aggregation:e.target.value as DashPanel['aggregation']})}>
          <option value="avg">Rata-rata</option><option value="peak">Maksimum / Puncak</option><option value="min">Minimum</option></select></label>}
        {panel.kind!=='rule'&&<fieldset className="dash-advanced"><legend>Pengaturan Grafik & Tampilan</legend>
          {panel.source==='metric'&&<label>Satuan tampilan<select value={panel.display_unit||''} onChange={e=>patch({display_unit:e.target.value||null})}>
            <option value="">Satuan asli ({sourceUnit||'—'})</option>
            {compatible.filter(u=>u.code!==sourceUnit).map(u=><option key={u.code} value={u.code}>{u.code} — {u.name}</option>)}
          </select></label>}
          <div className="dash-editor-grid"><label>Posisi Legenda<select value={panel.legend||'bottom'} onChange={e=>patch({legend:e.target.value as DashPanel['legend']})}>
            <option value="bottom">Bawah</option><option value="top">Atas</option><option value="right">Kanan</option><option value="hidden">Sembunyikan</option>
          </select></label><label>Angka desimal<select value={panel.decimals??2} onChange={e=>patch({decimals:Number(e.target.value)})}>
            {[0,1,2,3,4].map(n=><option value={n} key={n}>{n}</option>)}
          </select></label></div>
          {['line','step','area'].includes(panel.kind)&&<label className="dash-option"><input type="checkbox" checked={panel.show_points||false} onChange={e=>patch({show_points:e.target.checked})}/> Tampilkan titik pengukuran</label>}
          {seriesToColor.length>0&&<div className="dash-colors"><strong>Warna per seri</strong>{seriesToColor.map((s,i)=><label key={s.code}>{s.name}<input type="color" value={panel.colors?.[s.code]||['#087f8c','#e78538','#7162b5','#2c8c61'][i%4]}
            onChange={e=>patch({colors:{...panel.colors,[s.code]:e.target.value}})}/></label>)}</div>}
          <p className="dash-tip">Warna, legenda, dan konversi hanya mengubah tampilan. Data asli tetap dalam satuan sumber.</p>
        </fieldset>}
        <fieldset className="dash-advanced"><legend>Gaya Panel & Tipografi</legend>
          <label>Preset<select value={panel.style_preset||'classic'} onChange={e=>patch({style_preset:e.target.value as DashPanel['style_preset']})}>
            <option value="classic">Klasik (default)</option><option value="dark">Gelap</option><option value="soft">Lembut</option>
          </select></label>
          <div className="dash-editor-grid"><label>Font<select value={panel.font_family||'system'} onChange={e=>patch({font_family:e.target.value as DashPanel['font_family']})}>
            <option value="system">Sans-serif</option><option value="mono">Monospace</option></select></label>
            <label>Ukuran Judul (px)<input type="number" min={11} max={24} value={panel.title_font_size??13}
              onChange={e=>patch({title_font_size:Number(e.target.value)})}/></label>
            <label>Ukuran Angka KPI (px)<input type="number" min={18} max={54} value={panel.value_font_size??32}
              onChange={e=>patch({value_font_size:Number(e.target.value)})}/></label></div>
          <div className="dash-colors">{([['text_color','Warna teks','#153d52'],['background_color','Latar panel','#ffffff'],['border_color','Bingkai','#d5e4e8']] as const).map(([key,label,initialColor])=>
            <label key={key}>{label}<input type="color" value={panel[key]||initialColor}
              onChange={e=>patch({[key]:e.target.value})}/><button type="button" className="btn secondary sm" onClick={()=>patch({[key]:null})}>Otomatis</button></label>)}</div>
          <p className="dash-tip">Pengaturan ini hanya mengubah tampilan dan tidak mengubah nilai pengukuran.</p>
        </fieldset>
        <div className="dash-editor-grid"><label>Lebar<select value={panel.w} onChange={e=>patch({w:Number(e.target.value) as DashPanel['w']})}>
          {Array.from({length:10},(_,i)=>i+3).map(w=><option value={w} key={w}>{w}/12</option>)}</select></label>
          <label>Tinggi<select value={panel.h} onChange={e=>patch({h:Number(e.target.value) as DashPanel['h']})}>
            <option value="1">Normal</option><option value="2">Tinggi</option><option value="3">Ekstra tinggi</option><option value="4">Sangat tinggi</option></select></label></div>
        {error&&<div role="alert" className="notice error">{error}</div>}
        <footer><button type="button" className="btn secondary" onClick={onClose}>Batal</button>
          <button className="btn primary" type="submit"><Save size={16}/> Terapkan ke Dashboard</button></footer>
      </form>
    </aside>
  </div>;
}
