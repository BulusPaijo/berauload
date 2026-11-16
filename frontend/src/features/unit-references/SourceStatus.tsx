import {useEffect,useState} from 'react';
import {api} from '../../api';

type Source = {unit_id:number;unit:string;status:'draft'|'verified'|'final'};
export type Status = {date:string;counts:{final:number;verified:number;draft:number};units:Source[]};
export default function SourceStatus({day,codes}:{day:string;codes:string[]}){
 const [status,setStatus]=useState<Status|null>(null);
 const key=codes.join(',');
 useEffect(()=>{let alive=true;
   if(!key){setStatus(null);return;}
   api<Status>(`/unit-references/status?day=${encodeURIComponent(day)}&codes=${encodeURIComponent(key)}`)
     .then(value=>{if(alive)setStatus(value)}).catch(()=>{if(alive)setStatus(null)});
   return()=>{alive=false};
 },[day,key]);
 if(!status?.units.length)return null;
 const c=status.counts;
 return <details className="unit-source-status"><summary>
   Sumber: {c.final} final, {c.verified} terverifikasi, {c.draft} draf
 </summary><ul>{status.units.map(u=><li key={u.unit_id}>{u.unit}: {u.status}</li>)}</ul></details>;
}

export function SourceStatusSummary({status}:{status:Status|null|undefined}){
 if(!status?.units.length)return null;
 const c=status.counts;
 return <details className="unit-source-status"><summary>
   Sumber: {c.final} final, {c.verified} terverifikasi, {c.draft} draf
 </summary><ul>{status.units.map(u=><li key={u.unit_id}>{u.unit}: {u.status}</li>)}</ul></details>;
}
