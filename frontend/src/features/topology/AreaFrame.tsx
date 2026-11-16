/** Pure visual group decoration; deliberately no link to readings or status. */
import type {TopologyArea} from './types';
const COLORS={teal:'#56cfc8',blue:'#75b6ff',amber:'#f3bf6d',green:'#81cf96',red:'#f38e91',gray:'#b8c9d5'};
const DASHES={solid:undefined,dashed:'12 7',dotted:'2 7'};
export default function AreaFrame({area:a,selected=false}:{area:TopologyArea;selected?:boolean}){
 const color=COLORS[a.color]||COLORS.gray;
 return <g aria-label={`Area visual ${a.title}`}>
  <rect x={a.x} y={a.y} width={a.w} height={a.h} rx={4}
   fill={color} fillOpacity={a.opacity/100} stroke={selected?'#ffffff':color}
   strokeWidth={selected?3:2} strokeDasharray={DASHES[a.border]} pointerEvents="none"/>
  <text x={a.x+12} y={a.y+24} fontSize={16} fontWeight={700} fill="#e8f9ff"
   stroke="#061726" strokeWidth={3} paintOrder="stroke" pointerEvents="none">{a.title}</text>
 </g>;
}
