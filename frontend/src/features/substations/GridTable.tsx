import type {GridColumn,HeaderBlock} from './grid.mjs';
import {allowedCell,garduTone,rowState} from './grid.mjs';
import type {Def,Substation,Visit} from './types';

type Props={rows:Substation[];cols:GridColumn[];plan:HeaderBlock[];visits:Record<number,Visit>;statuses:Record<number,string>;
 conflicts:Record<number,unknown>;picked:number[];editable:boolean;flags:Def[];raw:(row:Substation,col:GridColumn)=>string;
 onPick:(ids:number[])=>void;onEdit:(id:number,col:GridColumn,text:string)=>void;onFlush:(id:number)=>void;
 onPaste:(e:React.ClipboardEvent<HTMLInputElement>,ri:number,ci:number)=>void;onKey:(e:React.KeyboardEvent<HTMLInputElement>,ri:number,ci:number)=>void;
 onFocusCell:(ri:number,ci:number)=>void;onResult:(visit:Visit)=>void;onConflict:(id:number)=>void};
/** Frozen: checkbox + Gardu on the left. Status sits at the far right (as in the approved design). */
export default function GridTable(p:Props){
 const all=p.rows.length>0&&p.rows.every(r=>p.picked.includes(r.id));
 const flagName=(code:string)=>p.flags.find(f=>f.code===code)?.name??code;
 return <div className="scroll-table substation-grid gx">
  <table><thead>
   <tr className="gx-top"><th className="gx-pick gx-freeze" rowSpan={2}><input type="checkbox" aria-label="Pilih semua baris" checked={all} onChange={e=>p.onPick(e.target.checked?p.rows.map(r=>r.id):[])}/></th>
    <th className="gx-name gx-freeze" rowSpan={2}>Gardu</th>
    {p.plan.map((b,i)=><th key={i} colSpan={b.span} scope="colgroup" className={'gx-block gx-l'+b.line+(b.tone?' gx-t-'+b.tone:'')}>{b.title}{b.unit&&<span className="gx-unit"> ({b.unit})</span>}</th>)}
    <th className="gx-status" rowSpan={2}>Status</th></tr>
   <tr className="gx-sub">{p.plan.flatMap((b,i)=>b.cells.map((c,j)=><th key={c.code+':'+c.line} title={c.code} className={'gx-l'+b.line+(b.tone?' gx-t-'+b.tone:'')+(j===0?' gx-first':'')}>
    {c.phase&&<i className={'phase-dot phase-'+c.phase} aria-hidden="true"/>}{c.sub||'nilai'}</th>))}</tr>
  </thead>
  <tbody>{p.rows.map((row,ri)=>{const visit=p.visits[row.id];const verified=visit?.state==='verified';
   const st=rowState({verified,conflict:!!p.conflicts[row.id],queue:p.statuses[row.id],filled:!!visit?.values?.length});
   return <tr key={row.id} className={'gx-row'+(st.tone==='danger'?' gx-row-danger':'')+(p.picked.includes(row.id)?' gx-row-picked':'')}>
    <td className="gx-pick gx-freeze"><input type="checkbox" aria-label={'Pilih '+row.code} checked={p.picked.includes(row.id)} onChange={e=>p.onPick(e.target.checked?[...p.picked,row.id]:p.picked.filter(x=>x!==row.id))}/></td>
    <th className="gx-name gx-freeze" scope="row"><b>{row.code}</b><small>{row.name} · {Number(row.power_kva)} kVA · {row.line_count} jur</small></th>
    {p.cols.map((col,ci)=>{const blocked=!allowedCell(row,col),lock=blocked||!p.editable||verified;const value=p.raw(row,col);const flag=value.startsWith('@')?value.slice(1):'';
     const tone=garduTone(col),first=ci===0||p.cols[ci-1].line!==col.line||garduTone(p.cols[ci-1])!==tone;
     if(blocked)return <td key={col.code+':'+col.line} className={'gx-cell gx-na'+(first?' gx-first':'')} aria-label="Jurusan tidak ada"/>;
     return <td key={col.code+':'+col.line} className={'gx-cell gx-l'+col.line+(tone?' gx-t-'+tone:'')+(first?' gx-first':'')+(flag?' gx-flagged':'')}>
      {flag&&<span className="gx-flag">{flagName(flag)}</span>}
      <input data-gridcell={`${ri}:${ci}`} disabled={lock} inputMode="decimal" size={6} value={flag?'':value}
       onFocus={()=>p.onFocusCell(ri,ci)} onChange={e=>p.onEdit(row.id,col,e.target.value)} onBlur={()=>p.onFlush(row.id)}
       onPaste={e=>p.onPaste(e,ri,ci)} onKeyDown={e=>p.onKey(e,ri,ci)} aria-label={`${row.code} · ${col.line?'Jurusan '+col.line+' · ':''}${col.name??col.label}`}/>
      {!lock&&<select className="gx-flag-pick" aria-label={`Penanda ${row.code} ${col.label}`} value={flag}
       onChange={e=>p.onEdit(row.id,col,e.target.value?'@'+e.target.value:'')}><option value="">Angka</option>{p.flags.filter(f=>f.active).map(f=><option key={f.code} value={f.code}>{f.name}</option>)}</select>}
     </td>;})}
    <td className={'gx-status gx-tone-'+st.tone}>{st.tone==='danger'&&p.conflicts[row.id]?<button className="link-btn" onClick={()=>p.onConflict(row.id)}>{st.label}</button>:st.label}
     {visit&&<button className="link-btn gx-calc" onClick={()=>p.onResult(visit)}>Hasil</button>}</td>
   </tr>;})}</tbody></table>
 </div>;
}
