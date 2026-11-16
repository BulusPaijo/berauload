import {useEffect,useState} from 'react';
import {api, type Metric} from '../../api';

export type UnitMetricReference = Metric & {unit_name:string;unit_level:'up3'|'ulp'|'kp';
  source:boolean;label:string;role_key:string|null};
export function useUnitMetricReferences(){
  const [metrics,setMetrics]=useState<UnitMetricReference[]>([]);
  useEffect(()=>{let mounted=true;
    api<{metrics:UnitMetricReference[]}>('/unit-references/metrics')
      .then(r=>{if(mounted)setMetrics(r.metrics)}).catch(()=>{if(mounted)setMetrics([])});
    return()=>{mounted=false};
  },[]);
  return metrics;
}
export function metricsForSelection(references:UnitMetricReference[], fallback:Metric[]){
  return references.length ? references : fallback;
}
