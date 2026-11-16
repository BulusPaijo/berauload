/** Pure UI-only conversion. Measurements, counts and original units never change. */
import type {DashPanel,LoadedPanel,PaneContext} from './types';

export function applyDisplayUnit(panel:DashPanel, ctx:PaneContext, original:LoadedPanel):LoadedPanel{
  if(!panel.display_unit||panel.source!=='metric')return original;
  const target=ctx.units?.find(u=>u.code===panel.display_unit&&u.active);
  if(!target)return original;
  const multiples:Record<string,number>={};
  for(const series of original.series){
    const source=ctx.units?.find(u=>u.code===series.unit);
    if(!source||source.dimension!==target.dimension||source.factor<=0)return original;
    multiples[series.key]=source.factor/target.factor;
  }
  const points=original.points.map(point=>{
    const next={...point};
    for(const series of original.series){
      const value=point[series.key];
      if(typeof value==='number')next[series.key]=value*multiples[series.key];
    }
    return next;
  });
  return {...original,points,unit:target.code,
    series:original.series.map(s=>({...s,unit:target.code})),
    coverage:`${original.coverage||''} Tampilan dikonversi ke ${target.code}; nilai asli tidak berubah.`};
}
