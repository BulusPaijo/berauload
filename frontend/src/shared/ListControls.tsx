import {Search} from 'lucide-react';
import './list-controls.css';

export type StatusOption = {value:string;label:string};
export const PAGE_SIZE = 20;

export default function ListControls({search,onSearch,status,onStatus,options,page,onPage,count}:{
  search:string;onSearch:(value:string)=>void;status:string;onStatus:(value:string)=>void;
  options:StatusOption[];page:number;onPage:(page:number)=>void;count:number;
}){
  const pages=Math.max(1,Math.ceil(count/PAGE_SIZE));
  return <div className="list-controls">
    <label className="list-controls-search"><Search size={16}/><input
      aria-label="Cari data" placeholder="Cari nama atau kode..." value={search}
      onChange={e=>{onSearch(e.target.value);onPage(1)}}/></label>
    <select aria-label="Filter status" value={status} onChange={e=>{onStatus(e.target.value);onPage(1)}}>
      {options.map(option=><option key={option.value} value={option.value}>{option.label}</option>)}
    </select>
    <div className="list-controls-paging">
      <span>{count} data · {page}/{pages} halaman</span>
      <button type="button" className="btn secondary sm" disabled={page<=1} onClick={()=>onPage(page-1)}>Sebelumnya</button>
      <button type="button" className="btn secondary sm" disabled={page>=pages} onClick={()=>onPage(page+1)}>Berikutnya</button>
    </div>
  </div>;
}
