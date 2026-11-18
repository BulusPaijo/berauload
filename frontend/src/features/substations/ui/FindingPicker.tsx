import {Fragment} from 'react';
import {findingSentence} from './findingText.mjs';
import './finding-picker.css';

type Rule={code:string;name:string;color?:string|null};
type Props={findings:Rule[];picked:string[];mode:string;onChange:(picked:string[],mode:string)=>void;title?:string};
/** 9d-5: finding chips + "salah satu / semua" segmented control + example sentence (Analisa & Export). */
export default function FindingPicker({findings,picked,mode,onChange,title='Temuan'}:Props){
 const m=mode==='all'?'all':'any';
 const toggle=(code:string)=>onChange(picked.includes(code)?picked.filter(c=>c!==code):[...picked,code],m);
 const names=findings.filter(f=>picked.includes(f.code)).map(f=>f.name);
 const s=findingSentence(names,m);
 return <div className="fp" role="group" aria-label={title}>
  <div className="fp-head"><b>{title}</b>
   <div className="fp-seg" role="radiogroup" aria-label="Cara mencocokkan temuan">
    {([['any','salah satu'],['all','semua']] as const).map(([k,label])=><button key={k} type="button" role="radio" aria-checked={m===k}
     className={m===k?'on':''} onClick={()=>onChange(picked,k)}>{label}</button>)}
   </div>
   {!!picked.length&&<button type="button" className="link-btn fp-clear" onClick={()=>onChange([],m)}>Hapus pilihan</button>}
  </div>
  <div className="fp-chips">{findings.map(f=>{const on=picked.includes(f.code);
   return <button key={f.code} type="button" aria-pressed={on} className={'fp-chip'+(on?' on':'')} onClick={()=>toggle(f.code)}
    style={on&&f.color?{borderColor:f.color,background:f.color+'1a'}:undefined}>
    <i style={{background:f.color??'#7b8a95'}} aria-hidden="true"/>{f.name}{on&&<span aria-hidden="true"> ✓</span>}</button>;})}
   {!findings.length&&<span className="fp-none">Belum ada temuan yang didefinisikan.</span>}</div>
  <p className="fp-say" aria-live="polite">{s.lead}{s.parts.length>0?' ':' — '}
   {s.parts.map((p,i)=><Fragment key={p}>{i>0&&<em className={'fp-join '+m}> {s.join} </em>}<b>{p}</b></Fragment>)}
   {s.parts.length>0&&s.tail&&<span> — {s.tail}</span>}{!s.parts.length&&<span>{s.tail}</span>}</p>
 </div>;
}
