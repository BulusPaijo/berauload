/** Reuse existing cookie authentication and CSRF transport. */
import {api,qs} from '../../api';
import type {TopologyDiagram,TopologyHour,TopologySeries,TopologyLayout,TopologyRevision,TopologyRule,DiagramUnit} from './types';

export const topologyApi={
  browse:()=>api<DiagramUnit[]>('/topology/browse'),
  linkTargets:()=>api<DiagramUnit[]>('/topology/link-targets'),
  list:()=>api<TopologyDiagram[]>('/topology'),
  one:(id:number)=>api<TopologyDiagram>(`/topology/${id}`),
  create:(name:string,description='')=>api<TopologyDiagram>('/topology',{
    method:'POST',body:JSON.stringify({name,description})}),
  save:(id:number,expected_version:number,name:string,description:string,layout:TopologyLayout)=>
    api<TopologyDiagram>(`/topology/${id}`,{method:'PUT',body:JSON.stringify({
      expected_version,name,description,layout})}),
  revisions:(id:number)=>api<TopologyRevision[]>(`/topology/${id}/revisions`),
  restore:(id:number,version:number,expected_version:number)=>
    api<TopologyDiagram>(`/topology/${id}/restore-version`,{
      method:'POST',body:JSON.stringify({version,expected_version})}),
  rules:()=>api<TopologyRule[]>('/engineering-rules'),
  hour:(id:number,day:string,hour:number)=>api<TopologyHour>(
    `/topology/${id}/data?${qs({day,hour})}`),
  series:(id:number,day:string)=>api<TopologySeries>(
    `/topology/${id}/series?${qs({day})}`),
};
