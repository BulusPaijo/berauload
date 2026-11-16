import {useEffect,useMemo,useRef,useState} from 'react';
import {activeUnitId,apiFetch,setCSRF} from '../../../api';
import type {DayData,User} from '../../../api';
import {HourQueue,backupKey,parseCell,readBackup,saveBackup} from './core.mjs';
import type {Backup} from './core.mjs';
import {setDirty} from './sessionActivity.mjs';

type Conflict={kode:string;nilai_anda:number|null;nilai_server:number|null;
 diubah_oleh:string|null;waktu:string|null};
type StatusMap=Record<number,string>;
const msg=(e:unknown)=>e instanceof Error?e.message:String(e);
const storage=()=>{try{return window.localStorage}catch{return null}};

export function useHourlyAutosave(day:string,user:User,enabled:boolean,
  onSaved:(hour:number,values:Record<string,number|null>,computed:Record<string,number|null>)=>void){
 const unitId=activeUnitId()??0;
 const key=backupKey(user.id,unitId,day);
 const [drafts,setDrafts]=useState<Record<string,string>>({});
 const [statuses,setStatuses]=useState<StatusMap>({});
 const [conflicts,setConflicts]=useState<Record<number,Conflict[]>>({});
 const [backup,setBackup]=useState<Backup|null>(null);
 const [otherTab,setOtherTab]=useState(false);
 const [sessionExpired,setSessionExpired]=useState(false);
 const [locked,setLocked]=useState(false);
 const [error,setError]=useState('');
 const draftsRef=useRef<Record<string,string>>({});
 const baseRef=useRef<Record<string,number|null>>({});
 const enabledRef=useRef(enabled);
 const onSavedRef=useRef(onSaved);
 const backupTimer=useRef<ReturnType<typeof setTimeout>|null>(null);
 enabledRef.current=enabled&&!locked;
 onSavedRef.current=onSaved;
 const persist=()=>saveBackup(storage(),key,draftsRef.current,baseRef.current);

 async function transmit(hour:number){
  const fields=Object.entries(draftsRef.current).filter(([k])=>k.startsWith(`${hour}:`));
  if(!fields.length)return;
  const values:Record<string,number|null>={};
  const base:Record<string,number|null>={};
  const raws:Record<string,string>={};
  try{for(const [k,raw] of fields){const code=k.slice(k.indexOf(':')+1);
    values[code]=parseCell(raw);base[code]=baseRef.current[k]??null;raws[k]=raw;}}
  catch(e){setError(msg(e));throw {status:422};}
  const overwrite=overridesRef.current[hour]||[];
  const response=await apiFetch(`/api/records/${day}/${hour}`,{
   method:'PUT',body:JSON.stringify({values,base,overrides:overwrite})});
  if(!response.ok){const body=await response.json().catch(()=>({}));
   const detail=body.detail??body;
   if(response.status===409){if(Array.isArray(detail.conflicts))
    setConflicts(v=>({...v,[hour]:detail.conflicts}));
    else{setLocked(true);setError(detail.message||String(detail)||'Hari terkunci');}}
   else if(response.status===401)setSessionExpired(true);
   else if(response.status<500)setError(typeof detail==='string'?detail:(detail.message||`HTTP ${response.status}`));
   throw {status:response.status};
  }
  const result=await response.json();
  const newer={...draftsRef.current};
  for(const [k,raw] of fields){const code=k.slice(k.indexOf(':')+1);
   baseRef.current[k]=values[code];
   if(newer[k]===raw)delete newer[k];
  }
  draftsRef.current=newer;setDrafts(newer);
  overridesRef.current[hour]=[];
  onSavedRef.current(hour,values,result.computed||{});
  persist();
 }
 const overridesRef=useRef<Record<number,string[]>>({});
 const queue=useMemo(()=>new HourQueue(transmit,(hour,status)=>{
   setStatuses(v=>({...v,[hour]:status==='tersimpan'
     ?`tersimpan ${new Date().toLocaleTimeString('id-ID',{hour:'2-digit',minute:'2-digit',timeZone:'Asia/Makassar'})}`:status}));
 },3000),[day,user.id,unitId]);
 useEffect(()=>()=>{queue.stop();persist()},[queue]);
 useEffect(()=>{setDirty(Object.keys(drafts).length>0);
  if(backupTimer.current)clearTimeout(backupTimer.current);
  backupTimer.current=setTimeout(persist,500);
  return()=>{if(backupTimer.current)clearTimeout(backupTimer.current)};
 },[drafts,key]);
 useEffect(()=>{const handle=(e:BeforeUnloadEvent)=>{if(Object.keys(draftsRef.current).length){
   persist();e.preventDefault();e.returnValue='';}};
  const other=(e:StorageEvent)=>{if(e.key===key)setOtherTab(true)};
  window.addEventListener('beforeunload',handle);window.addEventListener('storage',other);
  return()=>{window.removeEventListener('beforeunload',handle);window.removeEventListener('storage',other);setDirty(false)};
 },[key]);

 function loaded(data:DayData){
  // Server data always wins until the user explicitly chooses Restore.
  draftsRef.current={};baseRef.current={};setDrafts({});setConflicts({});
  setStatuses({});setLocked(false);setError('');
  const candidate=readBackup(storage(),key);
  const different=candidate&&Object.entries(candidate.drafts).some(([k,raw])=>{
   const [hour,code]=k.split(':');
   return raw!==(data.hours[Number(hour)]?.values[code]==null?'':String(data.hours[Number(hour)]?.values[code]));
  });
  setBackup(different?candidate:null);
 }
 function edit(hour:number,code:string,raw:string,server:number|null){
  const k=`${hour}:${code}`;
  if(!(k in baseRef.current))baseRef.current[k]=server;
  const next={...draftsRef.current,[k]:raw};draftsRef.current=next;setDrafts(next);
  if(enabledRef.current)queue.mark(hour);
 }
 function restore(){if(!backup)return;
  baseRef.current={...backup.base};draftsRef.current={...backup.drafts};
  setDrafts({...backup.drafts});setBackup(null);
  if(enabledRef.current)for(const k of Object.keys(backup.drafts))queue.mark(Number(k.split(':')[0]));
 }
 function discard(){setBackup(null);saveBackup(storage(),key,{},{});}
 function resolve(hour:number,code:string,useServer:boolean){
  const item=conflicts[hour]?.find(x=>x.kode===code);if(!item)return;
  const k=`${hour}:${code}`;
  baseRef.current[k]=item.nilai_server;
  if(useServer){const next={...draftsRef.current};delete next[k];draftsRef.current=next;
   setDrafts(next);onSavedRef.current(hour,{[code]:item.nilai_server},{});}
  else overridesRef.current[hour]=[...new Set([...(overridesRef.current[hour]||[]),code])];
  const rest=conflicts[hour].filter(x=>x.kode!==code);
  setConflicts(c=>({...c,[hour]:rest}));
  if(!rest.length&&enabledRef.current)void queue.resolve(hour);
 }
 async function login(username:string,password:string){
  try{const response=await apiFetch('/api/auth/login',{method:'POST',
    body:JSON.stringify({username,password})});
   if(!response.ok)throw new Error('Login gagal');
   const result=await response.json();
   if(result.user.id!==user.id){setError('Akun berbeda. Isian tetap milik pengguna sebelumnya dan tidak dikirim.');return false;}
   setCSRF(result.csrf);setSessionExpired(false);setError('');
   await queue.resume();return true;
  }catch(e){setError(msg(e));return false;}
 }
 return {drafts,statuses,conflicts,backup,otherTab,sessionExpired,locked,error,
   edit,loaded,restore,discard,resolve,login,flush:(hour:number)=>queue.flush(hour),
   saveAll:()=>queue.flushAll(),persist,dirtyHours:[...new Set(Object.keys(drafts).map(k=>Number(k.split(':')[0])))].sort((a,b)=>a-b)};
}
