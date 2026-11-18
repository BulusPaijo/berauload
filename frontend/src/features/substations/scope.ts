import {useEffect,useState} from 'react';
import {api,activeUnitId} from '../../api';

/** 9d-4: what the active unit may write (own unit; an ULP also its KPs) and whether it manages master data. */
export type Scope={data_unit_ids:number[];can_manage_master:boolean;units:{id:number;name:string;level:string;parent_id:number|null}[]};
const cache=new Map<number,Promise<Scope>>();
export function loadScope(){const unit=activeUnitId()??0;
 if(!cache.has(unit)){const p=api<Scope>('/substations/scope');cache.set(unit,p);p.catch(()=>cache.delete(unit));}
 return cache.get(unit)!;}
export function useScope(){const unit=activeUnitId();const [scope,setScope]=useState<Scope|null>(null);
 useEffect(()=>{let live=true;loadScope().then(s=>live&&setScope(s)).catch(()=>live&&setScope({data_unit_ids:[],can_manage_master:false,units:[]}));return()=>{live=false}},[unit]);
 return scope;}
export const canWrite=(scope:Scope|null,unitId:number|undefined|null)=>!!scope&&unitId!=null&&scope.data_unit_ids.includes(unitId);
