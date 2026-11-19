import {useEffect,useRef} from 'react';
import type {ReactNode} from 'react';
import './ui.css';

/** Stack of open drawers: only the top one reacts to Esc/Tab, so a panel opened over another closes alone. */
const open:object[]=[];
type Props={title:string;subtitle?:string;onClose:()=>void;children:ReactNode;footer?:ReactNode;wide?:boolean};
/** Side panel: Esc closes, focus moves inside and stays inside (Tab wraps). */
export default function Drawer({title,subtitle,onClose,children,footer,wide}:Props){
 const box=useRef<HTMLElement>(null),token=useRef({});
 useEffect(()=>{const me=token.current;open.push(me);return()=>{const i=open.indexOf(me);if(i>=0)open.splice(i,1)}},[]);
 useEffect(()=>{
  const me=token.current;
  const prev=document.activeElement as HTMLElement|null;
  box.current?.querySelector<HTMLElement>('input,select,textarea,button')?.focus();
  const key=(e:KeyboardEvent)=>{
   if(open[open.length-1]!==me)return;
   if(e.key==='Escape'){onClose();return;}
   if(e.key!=='Tab'||!box.current)return;
   const items=[...box.current.querySelectorAll<HTMLElement>('input:not([disabled]),select:not([disabled]),textarea,button:not([disabled]),a[href]')];
   if(!items.length)return;const first=items[0],last=items[items.length-1];
   if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
   else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
  };
  window.addEventListener('keydown',key);
  return()=>{window.removeEventListener('keydown',key);prev?.focus?.();};
 },[onClose]);
 return <><div className="ui-drawer-backdrop" onClick={onClose}/>
  <aside ref={box} className={'ui-drawer'+(wide?' wide':'')} role="dialog" aria-modal="true" aria-label={title}>
   <header><div><h3>{title}</h3>{subtitle&&<p>{subtitle}</p>}</div><button className="ui-icon-btn" aria-label="Tutup" onClick={onClose}>✕</button></header>
   <div className="ui-drawer-body">{children}</div>
   {footer&&<footer>{footer}</footer>}
  </aside></>;
}
