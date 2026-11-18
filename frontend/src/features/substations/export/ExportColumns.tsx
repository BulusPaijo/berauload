import {useMemo,useState} from 'react';
import {ArrowDown,ArrowUp,Plus,Search,Trash2} from 'lucide-react';
import {addColumn,groupCatalog,moveColumn,removeColumn,renameColumn} from './spec.mjs';
import type {CatalogItem,ExportColumn} from './spec.mjs';

type Props={items:CatalogItem[];columns:ExportColumn[];shape:string;onChange:(next:ExportColumn[])=>void};
export default function ExportColumns({items,columns,shape,onChange}:Props){
 const [search,setSearch]=useState('');
 const labels=useMemo(()=>new Map(items.map(i=>[i.key,i.label])),[items]);
 const groups=groupCatalog(items,columns.map(c=>c.key),search,shape);
 return <div className="export-columns">
  <section className="panel export-section"><h3>Kolom tersedia</h3>
   <div className="export-search"><Search size={17}/><input aria-label="Cari kolom" placeholder="Cari kolom atau kode" value={search} onChange={e=>setSearch(e.target.value)}/></div>
   <div className="export-available">{groups.map(g=><div key={g.group} className="export-group"><h4>{g.group}</h4>
    {g.entries.slice(0,80).map(item=><button key={item.key} className="export-add" onClick={()=>onChange(addColumn(columns,item.key))}><Plus size={15}/><span>{item.label}</span></button>)}
    {g.entries.length>80&&<p className="muted small">{g.entries.length-80} lagi — persempit pencarian.</p>}</div>)}
    {!groups.length&&<p className="muted small">Tidak ada kolom lain yang cocok.</p>}</div>
  </section>
  <section className="panel export-section"><h3>Kolom dipilih ({columns.length})</h3>
   <p className="muted small">Urutan di sini adalah urutan di berkas. Ketik judul baru bila ingin mengganti nama kolom.</p>
   {!columns.length&&<div className="export-empty"><b>Belum ada kolom</b><span>Pilih kolom dari daftar kiri.</span></div>}
   <div className="export-selected">{columns.map((c,i)=><div className="export-selected-item" key={c.key}>
    <div className="export-selected-top"><b>{i+1}. {labels.get(c.key)??c.key}</b><div className="export-move">
     <button title="Naik" aria-label="Naikkan kolom" disabled={i===0} onClick={()=>onChange(moveColumn(columns,i,-1))}><ArrowUp size={15}/></button>
     <button title="Turun" aria-label="Turunkan kolom" disabled={i===columns.length-1} onClick={()=>onChange(moveColumn(columns,i,1))}><ArrowDown size={15}/></button>
     <button title="Hapus kolom" aria-label="Hapus kolom" onClick={()=>onChange(removeColumn(columns,c.key))}><Trash2 size={15}/></button></div></div>
    <input aria-label={`Judul ${labels.get(c.key)??c.key}`} placeholder="Judul bawaan" maxLength={80} value={c.header??''} onChange={e=>onChange(renameColumn(columns,c.key,e.target.value))}/>
   </div>)}</div>
  </section>
 </div>;
}
