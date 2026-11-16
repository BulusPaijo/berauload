import type {Metric} from '../../api';
import type {UnitMetricReference} from './useUnitMetricReferences';

type M = Metric | UnitMetricReference;
export function unitMetricGroups(metrics:M[]){
  const groups=new Map<string,M[]>();
  for(const metric of metrics){
    const unit='unit_name' in metric ? String(metric.unit_name) : 'Unit Aktif';
    groups.set(unit,[...(groups.get(unit)||[]),metric]);
  }
  return [...groups.entries()].map(([name,items])=>({name,items}));
}
export default function UnitMetricOptions({metrics}:{metrics:M[]}){
  return <>{unitMetricGroups(metrics).map(group=><optgroup label={group.name} key={group.name}>
    {group.items.map(metric=><option key={metric.code} value={metric.code}>
      {'label' in metric?String(metric.label):`${group.name} - ${metric.name}`} ({metric.unit})
    </option>)}
  </optgroup>)}</>;
}
