import {useEffect,useState} from 'react';
import {api,setActiveUnit, type User} from '../../api';
import {pickUnit,flattenUnits, type UnitNode} from './unitSelection.mjs';
export default function useActiveUnit(user:User|null,beforeSwitch:()=>boolean,onError:(error:string)=>void){
 const [unitTree,setUnitTree]=useState<UnitNode[]>([]);
 const [unit,setUnit]=useState<UnitNode|null>(null);
 const [unitRevision,setUnitRevision]=useState(0);
 const [unitReady,setUnitReady]=useState(false);
 useEffect(()=>{
  if(!user){setActiveUnit(null);setUnit(null);setUnitReady(false);return;}
  let cancelled=false;setUnitReady(false);setUnit(null);setUnitTree([]);setActiveUnit(null);
  api<UnitNode[]>('/org-units/selectable').then(tree=>{
   if(cancelled)return;
   let saved:number|null=null;
   try{const stored=localStorage.getItem(`berauload:unit:${user.id}`);
    saved=stored&&/^\d+$/.test(stored)?Number(stored):null}catch{}
   const selected=pickUnit(tree,saved);setUnitTree(tree);setUnit(selected);
   setActiveUnit(selected?.id??null);setUnitReady(true);setUnitRevision(n=>n+1);
  }).catch(error=>{if(!cancelled){onError(String(error));setUnitReady(true)}});
  return()=>{cancelled=true};
 },[user]);
 function chooseUnit(id:number){
  const next=flattenUnits(unitTree).find(item=>item.id===id&&item.active);
  if(!next||!user||!beforeSwitch())return;
  setUnit(next);setActiveUnit(next.id);
  try{localStorage.setItem(`berauload:unit:${user.id}`,String(next.id))}catch{}
  setUnitRevision(n=>n+1);
 }
 return {unitTree,unit,unitRevision,unitReady,chooseUnit};
}
