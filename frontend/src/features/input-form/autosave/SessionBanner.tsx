import {useEffect,useState} from 'react';
import {api,setCSRF} from '../../../api';
import {markActive,hasDirty,activityAt} from './sessionActivity.mjs';
import {shouldHeartbeat,showExpiryBanner} from './core.mjs';

export default function SessionBanner(){
 const [expires,setExpires]=useState('');
 const [clock,setClock]=useState(Date.now());
 const [error,setError]=useState('');
 async function heartbeat(){
  try{const r=await api<{expires_at:string;csrf:string}>('/auth/me');
   setExpires(r.expires_at);setCSRF(r.csrf);setError('');}
  catch{setError('Sesi tidak dapat diperpanjang. Pastikan isian tersimpan.');}
 }
 useEffect(()=>{
  const activity=()=>markActive();
  window.addEventListener('pointerdown',activity);window.addEventListener('keydown',activity);
  void heartbeat();
  const heartbeatTimer=setInterval(()=>{
   if(shouldHeartbeat(activityAt(),hasDirty(),Date.now()))void heartbeat();
  },10*60*1000);
  const clockTimer=setInterval(()=>setClock(Date.now()),60*1000);
  return()=>{window.removeEventListener('pointerdown',activity);window.removeEventListener('keydown',activity);
   clearInterval(heartbeatTimer);clearInterval(clockTimer);};
 },[]);
 if(!error&&(!expires||!showExpiryBanner(expires,clock)))return null;
 return <div className="notice warning session-banner" role="status">
  {error||`Sesi akan berakhir pukul ${new Date(expires).toLocaleTimeString('id-ID',{
    hour:'2-digit',minute:'2-digit',timeZone:'Asia/Makassar'})} WITA`}
  <button className="btn secondary sm" onClick={()=>void heartbeat()}>Perpanjang</button>
 </div>;
}
