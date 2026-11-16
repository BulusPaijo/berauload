export type Role='admin'|'verifier'|'operator'|'management';
export type User={id:number;username:string;name:string;role:Role};
export type Metric={id:number;code:string;name:string;unit:string;group:string;mode:string;active:boolean;asset_id:number|null;unit_id?:number|null;role_key?:string|null};
export type Asset={id:number;code:string;name:string;kind:string;active:boolean;unit_id?:number|null};
export type Catalog={assets:Asset[];metrics:Metric[];roles?:Record<string,string>};
export const mainCode=(catalog:Catalog,role:'system.load'|'system.capacity')=>catalog.roles?.[role]||'';
export type EquipmentKind={id:number;code:string;name:string;active:boolean;display_order:number};
export type Hour={hour:number;values:Record<string,number>;sources:Record<string,string>};
export type DayData={date:string;status:string;filled_hours:number;hours:Hour[]};
export type Dashboard={year:number;month:number;peak_kw:number|null;peak_at:string|null;min_kw:number|null;avg_kw:number|null;readings_count:number;expected_hours_to_date:number;coverage_pct:number|null;final_days:number;daily:{date:string;peak_kw:number;avg_kw:number;count:number}[]};
export type Point={period:string;min:number;peak:number;avg:number;count:number};
export type Series={metric:string;unit:string;granularity:string;start:string;end:string;data:Point[]};
let unitId:number|null=null;
export const setActiveUnit=(id:number|null)=>{unitId=id};
export const activeUnitId=()=>unitId;
export const unitCacheKey=(key:string)=>`${unitId??'default'}:${key}`;
export let csrf='';
export const setCSRF=(value:string)=>{csrf=value};
export async function apiFetch(path:string,init:RequestInit={}):Promise<Response>{
  const headers=new Headers(init.headers||{});
  if(unitId!==null)headers.set('X-Unit-Id',String(unitId));
  if(!(init.body instanceof FormData)&&init.body) headers.set('Content-Type','application/json');
  if(init.method && !['GET','HEAD'].includes(init.method.toUpperCase()) && csrf)headers.set('X-CSRF-Token',csrf);
  try{return await fetch(path,{...init,headers,credentials:'same-origin'});}
  catch{throw new Error('Tidak dapat menghubungi server. Periksa jaringan.');}
}
export async function api<T=any>(path:string,init:RequestInit={}):Promise<T>{
  const response=await apiFetch('/api'+path,init);
  if(!response.ok){const data=await response.json().catch(()=>({}));
    const detail=Array.isArray(data.detail)?data.detail.map((x:any)=>x.msg).join('; '):data.detail;
    throw new Error(detail||`HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}
export async function downloadApi(path:string,filename:string){
 const result=await apiFetch('/api'+path);
 if(!result.ok){const body=await result.json().catch(()=>({}));throw new Error(body.detail||`HTTP ${result.status}`)}
 const blob=await result.blob(),url=URL.createObjectURL(blob),link=document.createElement('a');
 link.href=url;link.download=filename;document.body.append(link);link.click();link.remove();
 setTimeout(()=>URL.revokeObjectURL(url),30000);
}
export const isoWita=()=>new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Makassar',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
export const months=['Januari','Februari','Maret','April','Mei','Juni','Juli','Agustus','September','Oktober','November','Desember'];
export const num=(v:number|null|undefined,digits=1)=>v==null?'—':new Intl.NumberFormat('id-ID',{maximumFractionDigits:digits}).format(v);
export const pct=(v:number|null|undefined)=>v==null?'—':`${num(v,1)}%`;
export const qs=(args:Record<string,string|number>)=>new URLSearchParams(Object.fromEntries(Object.entries(args).map(([k,v])=>[k,String(v)]))).toString();
