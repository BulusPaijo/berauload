/** Neutral electrical glyphs: no inferred breaker state or source connectivity. */
import type {TopologySymbol} from './types';

type Props={symbol:TopologySymbol};
const common={fill:'none',stroke:'#9bd5ea',strokeWidth:3,strokeLinecap:'round' as const};

function Glyph({symbol:s}:{symbol:TopologySymbol}){
 const cx=s.w/2,cy=s.h/2,r=Math.max(10,Math.min(s.w,s.h)*.28);
 switch(s.type){
  case 'generator':return <><circle cx={cx} cy={cy} r={r} {...common}/><path d={`M ${cx-r*.7} ${cy} Q ${cx-r*.35} ${cy-r*.75} ${cx} ${cy} T ${cx+r*.7} ${cy}`} {...common}/></>;
  case 'transformer':return <><circle cx={cx-r*.43} cy={cy} r={r*.72} {...common}/><circle cx={cx+r*.43} cy={cy} r={r*.72} {...common}/></>;
  case 'busbar':return <line x1={5} x2={s.w-5} y1={cy} y2={cy} stroke="#f6bb54" strokeWidth={8} strokeLinecap="round"/>;
  case 'breaker':return <><line x1={cx} x2={cx} y1={5} y2={cy-r*.9} {...common}/><rect x={cx-r*.8} y={cy-r*.9} width={r*1.6} height={r*1.8} rx={3} fill="#19374a" stroke="#9bd5ea" strokeWidth={3}/><line x1={cx} x2={cx} y1={cy-r*.5} y2={cy+r*.5} stroke="#9bd5ea" strokeWidth={2}/><line x1={cx} x2={cx} y1={cy+r*.9} y2={s.h-5} {...common}/></>;
  case 'capacitor':return <><line x1={cx} x2={cx} y1={8} y2={cy-r*.3} {...common}/><line x1={cx-r} x2={cx+r} y1={cy-r*.3} y2={cy-r*.3} {...common}/><line x1={cx-r} x2={cx+r} y1={cy+r*.3} y2={cy+r*.3} {...common}/><line x1={cx} x2={cx} y1={cy+r*.3} y2={s.h-8} {...common}/></>;
  case 'incoming':return <><line x1={cx} x2={cx} y1={5} y2={s.h-15} {...common}/><path d={`M ${cx-10} ${s.h-24} L ${cx} ${s.h-10} L ${cx+10} ${s.h-24}`} {...common}/></>;
  case 'feeder':return <><line x1={cx} x2={cx} y1={5} y2={s.h-15} {...common}/><path d={`M ${cx-10} ${s.h-26} L ${cx} ${s.h-10} L ${cx+10} ${s.h-26}`} {...common}/></>;
  case 'load':return <><rect x={cx-r} y={cy-r*.7} width={r*2} height={r*1.4} rx={4} {...common}/><path d={`M ${cx-r*.6} ${cy} H ${cx+r*.6}`} {...common}/></>;
 }
}

export default function SymbolGlyph({symbol}:Props){
 const {x,y,w,h,rotation,label}=symbol;
 return <g className="topo-symbol" transform={`translate(${x},${y})`} aria-label={`${label} (${symbol.type})`}>
  <g transform={`rotate(${rotation},${w/2},${h/2})`}><Glyph symbol={symbol}/></g>
  <text className="topo-symbol-label" textAnchor="middle" x={w/2} y={h+16}>{label}</text>
 </g>;
}
