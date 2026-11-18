import {useState} from 'react';
type Props={file:File|null;accept:string;onFile:(f:File|null)=>void;hint:string};
export default function FileDrop({file,accept,onFile,hint}:Props){
 const [over,setOver]=useState(false);
 return <label className={'ui-drop'+(over?' over':'')} onDragOver={e=>{e.preventDefault();setOver(true)}} onDragLeave={()=>setOver(false)}
  onDrop={e=>{e.preventDefault();setOver(false);onFile(e.dataTransfer.files?.[0]??null)}}>
  <input type="file" accept={accept} onChange={e=>onFile(e.target.files?.[0]??null)}/>
  <span className="ui-drop-icon" aria-hidden="true">⬆</span>
  <b>{file?file.name:'Seret berkas ke sini'}</b>
  <span>{file?`${Math.ceil(file.size/1024)} KB · klik untuk mengganti`:<>atau <u>pilih berkas</u> · {hint}</>}</span>
 </label>;
}
