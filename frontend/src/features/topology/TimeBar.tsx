/** Compact WITA historical playback; retains all time controls. */
import {ChevronLeft,ChevronRight,Pause,Play,Info} from 'lucide-react';
import {hourLabel,dayStatus} from './viewerFormatting.mjs';
type Props={day:string;hour:number;playing:boolean;status:string|null;busy:boolean;
 setDay:(day:string)=>void;setHour:(hour:number)=>void;setPlaying:(on:boolean)=>void};
export default function TimeBar({day,hour,playing,status,busy,setDay,setHour,setPlaying}:Props){
 return <section className="topo-timebar topo-time-compact" aria-label="Pemilihan waktu pengukuran">
  <div className="topo-time-controls">
   <label className="topo-date-label"><span className="topo-sr-only">Tanggal</span><input type="date" value={day}
    onChange={e=>setDay(e.target.value)} aria-label="Tanggal data WITA"/></label>
   <button type="button" aria-label="Jam sebelumnya" onClick={()=>setHour(Math.max(0,hour-1))} disabled={hour===0}><ChevronLeft size={17}/></button>
   <button type="button" className="topo-play" aria-label={playing?'Jeda pemutaran':'Putar pemutaran jam'}
    onClick={()=>setPlaying(!playing)}>{playing?<Pause size={16}/>:<Play size={16}/>}<span className="topo-action-label">{playing?'Jeda':'Putar'}</span></button>
   <button type="button" aria-label="Jam berikutnya" onClick={()=>setHour(Math.min(23,hour+1))} disabled={hour===23}><ChevronRight size={17}/></button>
   <input className="topo-hour-slider" aria-label="Jam pengukuran 00 hingga 23 WITA" type="range" min={0} max={23} step={1}
    value={hour} onChange={e=>setHour(Number(e.target.value))}/>
   <output className="topo-hour-output">{hourLabel(hour)} WITA</output>
   <span className={`topo-compact-day topo-day-${status||'unknown'}`} title={`Status hari: ${dayStatus(status)}`}>
    <Info size={14}/><span className="topo-action-label">{dayStatus(status)}{busy?' · memuat':''}</span>
   </span>
  </div>
 </section>;
}
