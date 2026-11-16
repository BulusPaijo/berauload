/** Independent historical readings; one explicitly labeled sparkline at a time. */
import {useEffect,useState} from 'react';
import type {TopologyBox,TopologyHour,TopologySeries,RuleStatus} from './types';
import {formatMetric} from './viewerFormatting.mjs';
import {rankRows,availableCount,sparkSegments} from './boxView.mjs';
import {boxHeight as layoutHeight} from './editorState.mjs';
export const boxHeight=(box:TopologyBox):number=>layoutHeight(box);
const statusText=(value:RuleStatus)=>value==='normal'?'Normal':value==='warning'?'Waspada':value==='critical'?'Kritis':null;
const valuesKind=(kind:string)=>kind==='metric'||kind==='summary'||kind==='ranking';
type Props={box:TopologyBox;data:TopologyHour|null;names:Record<string,string>;
 series?:TopologySeries|null;onDetails:(box:TopologyBox)=>void};
function Sparkline({code,series,name,count,index}:{code:string;series:TopologySeries|null|undefined;
 name:string;count:number;index:number}){
 const paths=sparkSegments(series?.series?.[code]);
 return <div className="topo-sparkline" aria-label={`Tren 24 jam ${name}, celah data tidak disambung`}>
  <div className="topo-spark-caption"><span title={name}>Tren: {name}</span><small>{index+1}/{count}</small></div>
  {paths.length?<svg width="100%" height="32" viewBox="0 0 195 34" preserveAspectRatio="none" role="img"
   aria-label={`Grafik mini ${name}; jam kosong tetap kosong`}>
   {paths.map((line,i)=>line.length===1?
    <circle key={i} cx={line[0][0]} cy={line[0][1]} r={2.8} fill="#58cfda"/>:
    <polyline key={i} fill="none" stroke="#58cfda" strokeWidth="1.9"
     strokeLinejoin="round" points={line.map(point=>point.join(',')).join(' ')}/>)}
  </svg>:<span>Tren tidak tersedia</span>}
 </div>;
}
function Legend(){return <div className="topo-legend-body">
 <div><i className="topo-legend-line level-unspecified"/>Garis: belum ditentukan</div>
 <div><i className="topo-legend-line level-20kv"/>Garis: label visual 20 kV</div>
 <small>Garis adalah gambar manual, bukan bukti sambungan atau status bertegangan.</small>
 </div>;}
export default function ParamBox({box,data,names,series,onDetails}:Props){
 const [activeCode,setActiveCode]=useState(box.metric_codes[0]||'');
 useEffect(()=>{if(!box.metric_codes.includes(activeCode))setActiveCode(box.metric_codes[0]||'')},[box.metric_codes,activeCode]);
 const status=box.rule_id==null?null:data?.rules[String(box.rule_id)]??null;
 const display=statusText(status),codes=box.metric_codes.slice(0,6);
 const available=availableCount(codes,data?.values);
 const ranking=box.kind==='ranking'?rankRows(codes,data?.values,data?.units):null;
 const ordered=ranking?ranking.rows.map(row=>row.code):codes;
 const hasValues=valuesKind(box.kind)&&codes.length>0;
 const selected=codes.includes(activeCode)?activeCode:codes[0];
 return <div className={`topo-param-box status-${status||'neutral'} ${hasValues?'has-trend':''}`}
  onClick={()=>{if(hasValues)onDetails(box)}}>
  <div className="topo-param-head"><span className="topo-box-dot"/>
   <strong title={box.title}>{box.title}</strong>{display&&<span className="topo-rule-chip">{display}</span>}
  </div>
  <div className="topo-param-body">
   {box.kind==='legend'?<Legend/>:box.kind==='text'?<div className="topo-param-muted">{box.title}</div>:
    ranking?.mixed?<div className="topo-param-muted">Satuan berbeda; peringkat tidak dapat dihitung.</div>:
    hasValues?<>
      {box.kind==='summary'&&<div className="topo-summary-count">Terisi {available} dari {codes.length} parameter</div>}
      {box.kind==='ranking'&&!ordered.length&&<div className="topo-param-muted">Belum ada pembacaan pada jam ini.</div>}
      {ordered.map((code,i)=>{
       const value=data?.values[code],unit=box.show_unit?data?.units[code]:'';
       return <button className={'topo-param-row'+(selected===code?' is-trend-selected':'')}
        type="button" key={code} title={`Tampilkan grafik mini ${names[code]||code}`}
        aria-pressed={selected===code} onClick={e=>{e.stopPropagation();setActiveCode(code)}}>
        <span title={code}>{ranking?`${i+1}. `:''}{names[code]||code.replaceAll('_',' ')}</span>
        <strong>{formatMetric(value,box.decimals)}{value!=null&&unit?<small> {unit}</small>:null}</strong>
       </button>;
      })}
    </>:<div className="topo-param-muted">Belum ada parameter dipilih.</div>}
  </div>
  {box.sparkline&&hasValues&&selected&&<Sparkline code={selected} series={series}
   name={names[selected]||selected.replaceAll('_',' ')} count={codes.length} index={codes.indexOf(selected)}/>}
  {hasValues&&<button className="topo-trend-trigger" type="button"
   onClick={e=>{e.stopPropagation();onDetails(box)}} aria-label={`Lihat tren 24 jam ${box.title}`}>
   Lihat tren 24 jam <span aria-hidden="true">↗</span>
  </button>}
 </div>;
}
