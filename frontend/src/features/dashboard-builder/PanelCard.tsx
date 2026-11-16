import {useEffect,useRef,useState} from 'react';
import {Area,AreaChart,Bar,BarChart,CartesianGrid,Legend,Line,LineChart,ResponsiveContainer,Tooltip,XAxis,YAxis} from 'recharts';
import {ArrowLeft,ArrowRight,GripVertical,Pencil,Trash2} from 'lucide-react';
import {num} from '../../api';
import type {DashPanel,PaneContext,LoadedPanel} from './types';
import {loadPanel} from './loadPanel';
import SourceStatus,{SourceStatusSummary} from '../unit-references/SourceStatus';
import {snapSize} from './layoutGeometry';

const PALETTE=['#087f8c','#e78538','#7162b5','#2c8c61'];
const getMessage=(e:unknown)=>e instanceof Error?e.message:String(e);

function singleValue(panel:DashPanel,result:LoadedPanel):number|null{
  const key=result.series[0]?.key;
  if(!key)return null;
  const valid=result.points.filter(row=>typeof row[key]==='number');
  if(!valid.length)return null;
  if(panel.source==='historical')return Number(valid[valid.length-1][key]);
  const values=valid.map(row=>Number(row[key]));
  if(panel.aggregation==='peak')return Math.max(...values);
  if(panel.aggregation==='min')return Math.min(...values);
  const countKey=key+'_count';
  const weights=valid.map(row=>Number(row[countKey]??1));
  const total=weights.reduce((a,b)=>a+b,0);
  return total>0?values.reduce((sum,value,i)=>sum+value*weights[i],0)/total:null;
}

function RuleContent({result}:{result:LoadedPanel}){
  const rule=result.rule;
  if(!rule)return <div className="dash-empty">Aturan tidak tersedia.</div>;
  return <div className="dash-rule">
    <div><strong>{num(rule.status_counts.critical||0,0)}</strong><span>Jam kritis</span></div>
    <div><strong>{num(rule.status_counts.warning||0,0)}</strong><span>Jam waspada</span></div>
    <div><strong>{num(rule.status_counts.normal||0,0)}</strong><span>Jam normal</span></div>
    <small>{rule.valid_hours}/{rule.expected_hours} jam valid. {rule.missing_or_invalid_hours} jam hilang/tidak valid.</small>
  </div>;
}

function GraphContent({panel,result}:{panel:DashPanel;result:LoadedPanel}){
  const rows=result.points;
  if(!rows.some(row=>result.series.some(s=>typeof row[s.key]==='number'))){
    return <div className="dash-empty">Belum ada pengukuran yang sesuai pada periode ini.</div>;
  }
  if(panel.kind==='stat'||panel.kind==='gauge'){
    const value=singleValue(panel,result);
    const measured=rows.length;
    const maxObserved=Math.max(0,...rows.map(row=>Number(row[result.series[0]?.key]||0)));
    const gaugePct=value===null?0:result.unit==='%'?Math.max(0,Math.min(100,value)):
      maxObserved>0?Math.max(0,Math.min(100,value/maxObserved*100)):0;
    return <div className="dash-stat"><strong>{value===null?'—':num(value,panel.decimals??2)} <small>{result.unit}</small></strong>
      <span>{panel.source==='historical'?'Nilai periode historis terakhir':panel.aggregation==='avg'?'Rata-rata':panel.aggregation==='min'?'Minimum':'Maksimum'} · {measured} interval</span>
      {panel.kind==='gauge'&&<><div className="dash-gauge" role="meter" aria-valuenow={value||0} aria-label="Nilai parameter"><i style={{width:`${gaugePct}%`}}/></div>
        <small>{result.unit==='%'?'Skala presentasi 0–100%.':'Skala relatif terhadap maksimum teramati, bukan batas operasi.'}</small></>}
    </div>;
  }
  if(panel.kind==='table')return <div className="dash-table"><table><thead><tr><th>Periode</th>{result.series.map(s=><th key={s.key}>{s.name}</th>)}</tr></thead>
    <tbody>{rows.slice(-50).map(r=><tr key={r.period}><td>{r.period}</td>{result.series.map(s=><td key={s.key}>{typeof r[s.key]==='number'?num(Number(r[s.key]),panel.decimals??2):'—'}</td>)}</tr>)}</tbody></table>
    <small>Maksimal 50 baris terakhir ditampilkan; seluruh data tetap di database.</small></div>;
  const children=result.series.map((series,i)=>{
    const props={key:series.key,name:series.name,dataKey:series.key,stroke:panel.colors?.[series.key]||PALETTE[i%PALETTE.length],
      fill:panel.colors?.[series.key]||PALETTE[i%PALETTE.length],isAnimationActive:false,connectNulls:false};
    if(panel.kind==='bar'||panel.kind==='stacked_bar')return <Bar {...props} key={series.key} stackId={panel.kind==='stacked_bar'?'total':undefined}/>;
    if(panel.kind==='area')return <Area {...props} key={series.key} type="monotone" fillOpacity={0.12}/>;
    return <Line {...props} key={series.key} type={panel.kind==='step'?'stepAfter':'monotone'} strokeWidth={2.3} dot={!!panel.show_points||rows.length<15}/>;
  });
  const ChartComponent=['bar','stacked_bar'].includes(panel.kind)?BarChart:panel.kind==='area'?AreaChart:LineChart;
  return <div className="dash-graph"><ResponsiveContainer width="100%" height="100%">
    <ChartComponent data={rows} margin={{top:8,right:12,left:2,bottom:5}}>
      <CartesianGrid strokeDasharray="3 4" stroke="#e5eff2" vertical={false}/>
      <XAxis dataKey="period" minTickGap={26} tick={{fontSize:10}} tickFormatter={v=>String(v).slice(-11)}/>
      <YAxis tick={{fontSize:10}} width={52} tickFormatter={v=>num(Number(v),panel.decimals??2)}/>
      <Tooltip labelFormatter={label=>`Waktu/periode (WITA): ${String(label)}`} formatter={v=>typeof v==='number'?`${num(v,panel.decimals??2)} ${result.unit}`:'—'}/>
      {panel.legend!=='hidden'&&<Legend layout={panel.legend==='right'?'vertical':'horizontal'} align={panel.legend==='right'?'right':'center'} verticalAlign={panel.legend==='top'?'top':panel.legend==='right'?'middle':'bottom'} wrapperStyle={{fontSize:11}}/>}{children}
    </ChartComponent>
  </ResponsiveContainer></div>;
}

type Props={panel:DashPanel;ctx:PaneContext;editing:boolean;onEdit:()=>void;
 onRemove:()=>void;onMove:(step:number)=>void;onResize:(w:number,h:number)=>void;
 onDragStart:(event:React.DragEvent)=>void;onDragEnd:()=>void;onDrop:(event:React.DragEvent)=>void};
export default function PanelCard({panel,ctx,editing,onEdit,onRemove,onMove,onResize,onDragStart,onDragEnd,onDrop}:Props){
  const [preview,setPreview]=useState<{w:number;h:number}|null>(null);
  const [over,setOver]=useState(false);
  const widget=useRef<HTMLElement|null>(null);
  const current=useRef<{w:number;h:number}|null>(null);
  function beginResize(event:React.PointerEvent<HTMLButtonElement>){
    if(!editing||!widget.current)return;
    event.preventDefault();event.stopPropagation();
    const node=widget.current;
    const grid=node.parentElement;
    if(!grid)return;
    const styles=window.getComputedStyle(grid);
    const gap=parseFloat(styles.columnGap)||14;
    const rowGap=parseFloat(styles.rowGap)||14;
    const cell=(grid.getBoundingClientRect().width-11*gap)/12+gap;
    const row=(parseFloat(styles.gridAutoRows)||260)+rowGap;
    const sx=event.clientX,sy=event.clientY;
    current.current={w:panel.w,h:panel.h};
    const onPointer=(e:PointerEvent)=>{
      const next=snapSize(panel.w,panel.h,e.clientX-sx,e.clientY-sy,cell,row);
      current.current=next;setPreview(next);
    };
    const stop=()=>{
      window.removeEventListener('pointermove',onPointer);
      window.removeEventListener('pointerup',stop);
      window.removeEventListener('pointercancel',cancel);
      const next=current.current;current.current=null;setPreview(null);
      if(next&&(next.w!==panel.w||next.h!==panel.h))onResize(next.w,next.h);
    };
    const cancel=()=>{
      window.removeEventListener('pointermove',onPointer);
      window.removeEventListener('pointerup',stop);
      window.removeEventListener('pointercancel',cancel);
      current.current=null;setPreview(null);
    };
    window.addEventListener('pointermove',onPointer);
    window.addEventListener('pointerup',stop,{once:true});
    window.addEventListener('pointercancel',cancel,{once:true});
  }
  const [result,setResult]=useState<LoadedPanel|null>(null);
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(true);
  const codes=panel.metric_codes.join(',');
  useEffect(()=>{
    let alive=true;setBusy(true);setError('');setResult(null);
    loadPanel(panel,ctx).then(data=>{if(alive)setResult(data)}).catch(e=>{if(alive)setError(getMessage(e))})
      .finally(()=>{if(alive)setBusy(false)});
    return()=>{alive=false};
  },[ctx.start,ctx.end,ctx.granularity,codes,panel.source,panel.source_id,panel.kind,panel.aggregation,panel.display_unit,ctx.units]);
  const size=preview||panel;
  const presets={classic:{bg:'#ffffff',text:'#1a4355',border:'#e1edf0'},
    dark:{bg:'#122b38',text:'#f2fbff',border:'#225769'},
    soft:{bg:'#eff8f8',text:'#18505b',border:'#bcdddd'}};
  const palette=presets[panel.style_preset||'classic'];
  const style={gridColumn:`span ${size.w}`,gridRow:`span ${size.h}`,
    '--panel-bg':panel.background_color||palette.bg,
    '--panel-fg':panel.text_color||palette.text,
    '--panel-border':panel.border_color||palette.border,
    '--panel-title-size':`${panel.title_font_size||13}px`,
    '--panel-value-color':panel.text_color||(panel.style_preset==='dark'?'#d4f6f7':'#087f8c'),
    '--panel-value-size':`${panel.value_font_size||32}px`,
    '--panel-font':panel.font_family==='mono'?'ui-monospace, monospace':'inherit'
  } as React.CSSProperties;
  return <section ref={widget} className={`dash-widget${editing?' is-editing':''}${over?' is-drop-target':''}`}
    style={style}
    onDragOver={editing?e=>{e.preventDefault();setOver(true)}:undefined}
    onDragLeave={()=>setOver(false)} onDrop={e=>{setOver(false);onDrop(e)}}>
    <header><div className="dash-title">{editing&&<span className="dash-drag-handle" title="Tarik untuk memindahkan panel" draggable onDragStart={onDragStart} onDragEnd={()=>{setOver(false);onDragEnd()}}><GripVertical size={17}/></span>}<b>{panel.title}</b></div>
      {editing&&<div className="dash-widget-actions"><button type="button" title="Geser kiri" onClick={()=>onMove(-1)}><ArrowLeft size={15}/></button>
        <button type="button" title="Geser kanan" onClick={()=>onMove(1)}><ArrowRight size={15}/></button>
        <select title="Lebar panel" aria-label={`Lebar panel ${panel.title}`} value={panel.w} onChange={e=>onResize(Number(e.target.value),panel.h)}>
          {Array.from({length:10},(_,i)=>i+3).map(w=><option key={w} value={w}>{w===12?'Penuh':`${w}/12`}</option>)}
        </select><select title="Tinggi panel" aria-label={`Tinggi panel ${panel.title}`} value={panel.h} onChange={e=>onResize(panel.w,Number(e.target.value))}>{[1,2,3,4].map(h=><option key={h} value={h}>{h} tinggi</option>)}</select><button type="button" title="Edit panel" onClick={onEdit}><Pencil size={15}/></button>
        <button type="button" title="Hapus panel" onClick={onRemove}><Trash2 size={15}/></button></div>}
    </header>
    <div className="dash-widget-main">{busy?<div className="dash-empty">Memuat data...</div>:
      error?<div className="notice error" role="alert">{error}</div>:
      !result?<div className="dash-empty">Tidak ada data</div>:
      panel.kind==='rule'?<RuleContent result={result}/>:<GraphContent panel={panel} result={result}/>}</div>
    {result?.coverage&&!error&&<p className="dash-note">{result.coverage}</p>}
    {panel.source==='metric'?<SourceStatus day={ctx.end} codes={panel.metric_codes}/>:<SourceStatusSummary status={result?.sourceStatus}/>}
    {editing&&<button type="button" className="dash-resize-handle" onPointerDown={beginResize}
      title="Tarik sudut untuk mengubah lebar dan tinggi" aria-label={`Ubah ukuran panel ${panel.title}`}>
      <span aria-hidden="true">◢</span></button>}
    {preview&&<span className="dash-size-preview">{preview.w}/12 × {preview.h} tinggi</span>}
  </section>;
}
