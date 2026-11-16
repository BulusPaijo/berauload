/** Existing popup preserved, with optional compatible-unit comparison. */
import {useEffect,useMemo,useState} from 'react';
import {X} from 'lucide-react';
import {CartesianGrid,Legend,Line,LineChart,ResponsiveContainer,Tooltip,XAxis,YAxis} from 'recharts';
import type {TopologyBox,TopologySeries} from './types';
import {topologyApi} from './topologyApi';
import {trendPoints} from './viewerFormatting.mjs';
import {comparisonAllowed,combinedTrendPoints} from './trendCompare.mjs';
const COLORS=['#5dd3e9','#f3b65c','#7ed3a6','#ba9af5','#f38e91','#f4db84'];
type Props={box:TopologyBox;diagramId:number;day:string;names:Record<string,string>;onClose:()=>void};
export default function TrendDrawer({box,diagramId,day,names,onClose}:Props){
 const [metric,setMetric]=useState(box.metric_codes[0]||'');
 const [compare,setCompare]=useState(false);
 const [data,setData]=useState<TopologySeries|null>(null);
 const [error,setError]=useState('');
 useEffect(()=>{setMetric(box.metric_codes[0]||'');setCompare(false)},[box.id,box.metric_codes]);
 useEffect(()=>{
  let active=true;setData(null);setError('');
  topologyApi.series(diagramId,day).then(result=>{if(active)setData(result)})
   .catch(e=>{if(active)setError(e instanceof Error?e.message:String(e))});
  return()=>{active=false};
 },[diagramId,day]);
 useEffect(()=>{
  function escape(e:KeyboardEvent){if(e.key==='Escape')onClose()}
  window.addEventListener('keydown',escape);return()=>window.removeEventListener('keydown',escape);
 },[onClose]);
 const compatible=data?comparisonAllowed(box.metric_codes,data.units):false;
 const multi=compare&&compatible&&box.metric_codes.length>1;
 const rows=useMemo(()=>multi?combinedTrendPoints(data,box.metric_codes):trendPoints(data,metric),
  [data,multi,box.metric_codes,metric]);
 const hasData=multi?rows.some(row=>box.metric_codes.some(code=>typeof row[code]==='number')):
  rows.some(row=>row.nilai!==null);
 return <div className="topo-modal-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)onClose()}}>
  <section className="topo-trend-dialog" role="dialog" aria-modal="true" aria-label={`Tren 24 jam ${box.title}`}>
   <div className="topo-dialog-head"><div><span>TREN HARIAN</span><h3>{box.title}</h3><p>{day} · 00:00–23:00 WITA</p></div>
    <button type="button" aria-label="Tutup tren" onClick={onClose}><X size={20}/></button>
   </div>
   <div className="topo-trend-options"><label className="topo-select-label">Parameter
    <select value={metric} onChange={e=>setMetric(e.target.value)} disabled={multi}>
     {box.metric_codes.map(code=><option key={code} value={code}>{names[code]||code.replaceAll('_',' ')}</option>)}
    </select></label>
    {box.metric_codes.length>1&&<label className="topo-trend-compare"><input type="checkbox" checked={compare}
     disabled={!data||!compatible} onChange={e=>setCompare(e.target.checked)}/> Bandingkan semua</label>}
   </div>
   {data&&!compatible&&box.metric_codes.length>1&&
    <p className="topo-chart-note">Satuan parameter berbeda; gunakan pemilih untuk melihat satu grafik secara bergantian.</p>}
   {error?<p className="topo-error" role="alert">{error}</p>:!data?<p className="topo-faint">Memuat 24 pembacaan...</p>:<>
    <div className="topo-trend-graph" role="img" aria-label="Grafik historis 24 jam; celah untuk data kosong">
     {hasData?<ResponsiveContainer width="100%" height="100%"><LineChart data={rows} margin={{top:15,right:20,bottom:5,left:0}}>
      <CartesianGrid stroke="#284457" strokeDasharray="4 5" vertical={false}/>
      <XAxis dataKey="jam" stroke="#b4cad6" tick={{fontSize:11}} interval={3}/>
      <YAxis stroke="#b4cad6" tick={{fontSize:11}} width={60} domain={['auto','auto']}/>
      <Tooltip contentStyle={{background:'#102a3d',border:'1px solid #395368',color:'#fff'}}
       formatter={(value,name)=>[value==null?'—':Number(value).toLocaleString('id-ID',{maximumFractionDigits:4})+
        ' '+(data.units[multi?String(name):metric]||''),multi?(names[String(name)]||String(name)):'Pembacaan']}/>
      {multi?<>
       <Legend formatter={value=>names[String(value)]||String(value)}/>
       {box.metric_codes.map((code,i)=><Line key={code} type="linear" name={code} dataKey={code}
        stroke={COLORS[i%COLORS.length]} strokeWidth={2.2} dot={false} connectNulls={false} isAnimationActive={false}/>)}
      </>:<Line type="linear" dataKey="nilai" stroke="#5dd3e9" strokeWidth={2.3}
       dot={{r:2.5,fill:'#5dd3e9'}} connectNulls={false} isAnimationActive={false}/>}
     </LineChart></ResponsiveContainer>:<div className="topo-no-trend">Tidak ada pembacaan pada 24 jam ini.</div>}
    </div>
    <p className="topo-chart-note">Angka 0 tetap 0; jam tanpa pembacaan tetap kosong. {multi?'Setiap warna mewakili satu parameter.':'Satuan: '+(data.units[metric]||'—')+'.'}</p>
   </>}
  </section>
 </div>;
}
