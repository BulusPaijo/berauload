type Props={value:string;onChange:(json:string)=>void};
const parse=(text:string):[string,string][]=>{try{const o=JSON.parse(text||'{}');return o&&typeof o==='object'&&!Array.isArray(o)?Object.entries(o).map(([k,v])=>[k,v==null?'':String(v)]):[]}catch{return []}};
const write=(pairs:[string,string][])=>JSON.stringify(Object.fromEntries(pairs.filter(([k])=>k.trim()).map(([k,v])=>[k.trim(),v])));
/** Name–value list stored as the same JSON object the API already accepts. */
export default function KeyValueEditor({value,onChange}:Props){
 const pairs=parse(value);
 const set=(i:number,part:0|1,text:string)=>{const next=pairs.map(p=>[...p] as [string,string]);next[i][part]=text;onChange(write(next));};
 return <div className="ui-kv">
  {pairs.map(([k,v],i)=><div className="ui-kv-row" key={i}><input aria-label="Nama atribut" placeholder="Nama" value={k} onChange={e=>set(i,0,e.target.value)}/><input aria-label="Nilai atribut" placeholder="Nilai" value={v} onChange={e=>set(i,1,e.target.value)}/>
   <button type="button" className="ui-icon-btn" aria-label={'Hapus atribut '+k} onClick={()=>onChange(write(pairs.filter((_,j)=>j!==i)))}>✕</button></div>)}
  <button type="button" className="btn secondary sm" onClick={()=>onChange(JSON.stringify({...Object.fromEntries(pairs),[`atribut_${pairs.length+1}`]:''}))}>+ Tambah atribut</button>
 </div>;
}
