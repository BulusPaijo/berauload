/** One history entry per intentional action; pointer moves commit only on release. */
import {useCallback,useState} from 'react';
import type {TopologyDiagram,TopologyLayout} from './types';
import {clone} from './editorState.mjs';

export type EditorSnapshot={name:string;description:string;layout:TopologyLayout};
type History={past:EditorSnapshot[];present:EditorSnapshot;future:EditorSnapshot[]};
const original=(diagram:TopologyDiagram):EditorSnapshot=>({
 name:diagram.name,description:diagram.description,layout:clone(diagram.layout)});
const MAX_UNDO=60;
export function useTopologyDraft(diagram:TopologyDiagram){
 const baseline=original(diagram);
 const [history,setHistory]=useState<History>(()=>({past:[],present:baseline,future:[]}));
 const apply=useCallback((operation:(old:EditorSnapshot)=>EditorSnapshot)=>{
  setHistory(h=>{
   const candidate=operation(clone(h.present));
   if(JSON.stringify(candidate)===JSON.stringify(h.present))return h;
   return {past:[...h.past,h.present].slice(-MAX_UNDO),present:candidate,future:[]};
  });
 },[]);
 const undo=useCallback(()=>setHistory(h=>h.past.length?{
  past:h.past.slice(0,-1),present:h.past[h.past.length-1],future:[h.present,...h.future]}:h),[]);
 const redo=useCallback(()=>setHistory(h=>h.future.length?{
  past:[...h.past,h.present].slice(-MAX_UNDO),present:h.future[0],future:h.future.slice(1)}:h),[]);
 const reset=useCallback(()=>setHistory({past:[],present:original(diagram),future:[]}),[diagram]);
 const dirty=JSON.stringify(history.present)!==JSON.stringify(baseline);
 return {draft:history.present,apply,undo,redo,reset,dirty,
  canUndo:history.past.length>0,canRedo:history.future.length>0};
}
