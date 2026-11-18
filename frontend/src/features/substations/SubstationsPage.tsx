import {useEffect,useState} from 'react';
import {api,activeUnitId} from '../../api';
import type {User} from '../../api';
import type {Definitions,Feeder} from './types';
import InputGrid from './InputGrid';
import MobileVisitForm from './MobileVisitForm';
import MasterPanel from './MasterPanel';
import VisitList from './VisitList';
import DefinitionSettings from './DefinitionSettings';
import FormulaSettings from './formulas/FormulaSettings';
import AnalysisPage from './analysis/AnalysisPage';
import MapPage from './map/MapPage';
import ExportPage from './export/ExportPage';
import WorkList from './work/WorkList';
import MonitoringPage from './work/MonitoringPage';
import {ClipboardEdit,MapPinned,TableProperties,ChartNoAxesCombined,SlidersHorizontal,Landmark,ListChecks,Smartphone,Download,ClipboardList,Activity} from 'lucide-react';
import './substations.css';

type Props={user:User;readonly:boolean;level:string};
const message=(error:unknown)=>error instanceof Error?error.message:String(error);
export default function SubstationsPage({user,readonly,level}:Props){
 const [tab,setTab]=useState(()=>new URLSearchParams(location.search).get('gardu_tab')||'input'),[defs,setDefs]=useState<Definitions|null>(null);
 const [feeders,setFeeders]=useState<Feeder[]>([]),[error,setError]=useState('');
 const [focused,setFocused]=useState<number|string|undefined>();
 const unitId=activeUnitId();
 const navigate=(next:string,id?:number|string)=>{setFocused(id);setTab(next);const q=new URLSearchParams(location.search);q.set('gardu_tab',next);if(next==='analysis'&&typeof id==='string')q.set('text',id);history.replaceState(null,'',location.pathname+'?'+q);};
 function reload(){Promise.all([api<Definitions>('/substations/definitions'),
  api<Feeder[]>('/substations/feeders')]).then(([d,f])=>{setDefs(d);setFeeders(f);setError('')}).catch(e=>setError(message(e)))}
 useEffect(reload,[unitId]);
 const canVerify=user.role==='admin'||user.role==='verifier';
 const onUnit=level!=='up3';
 return <div className="page-space substation-page"><div className="page-top"><div><div className="eyebrow">OPERASIONAL / PENGUKURAN GARDU</div><h2>Pengukuran Gardu Distribusi</h2><p>Pengelolaan master dan pengisian pengukuran gardu secara terpusat, akurat, dan terverifikasi.</p></div></div>
  <nav className="substation-subnav" aria-label="Menu Pengukuran Gardu"><button className={tab==='input'?'active':''} onClick={()=>navigate('input')}><ClipboardEdit size={16}/> Input</button><button className={tab==='mobile'?'active':''} onClick={()=>navigate('mobile')}><Smartphone size={16}/> Form ponsel</button><button className={tab==='master'?'active':''} onClick={()=>navigate('master')}><Landmark size={16}/> Master</button><button className={tab==='visits'?'active':''} onClick={()=>navigate('visits')}><ListChecks size={16}/> Pengukuran</button><button className={tab==='analysis'?'active':''} onClick={()=>navigate('analysis')}><ChartNoAxesCombined size={16}/> Analisa</button><button className={tab==='map'?'active':''} onClick={()=>navigate('map')}><MapPinned size={16}/> Peta</button><button className={tab==='work'?'active':''} onClick={()=>navigate('work')}><ClipboardList size={16}/> Tindak lanjut</button><button className={tab==='monitor'?'active':''} onClick={()=>navigate('monitor')}><Activity size={16}/> Pemantauan</button><button className={tab==='export'?'active':''} onClick={()=>navigate('export')}><Download size={16}/> Export</button>{user.role==='admin'&&<button className={tab==='settings'?'active':''} onClick={()=>navigate('settings')}><SlidersHorizontal size={16}/> Definisi</button>}<button className={tab==='formulas'?'active':''} onClick={()=>navigate('formulas')}><TableProperties size={16}/> Rumus & Kategori</button></nav>
  {error&&<div className="notice error">{error} <button className="btn secondary sm" onClick={reload}>Coba lagi</button></div>}
  {!onUnit&&tab!=='settings'&&<div className="notice info">Pilih ULP atau KP untuk mengisi atau mengatur gardu. UP3 hanya membaca data unit bawah.</div>}
  {readonly&&<div className="notice info">Hanya lihat. Anda dapat membaca data gardu dalam kewenangan unit ini.</div>}
  {defs?(<>{tab==='input'&&onUnit&&<InputGrid key={`${unitId}:input`} user={user} defs={defs} feeders={feeders} readonly={readonly} onNavigate={navigate}/>}
   {tab==='mobile'&&onUnit&&<MobileVisitForm defs={defs} readonly={readonly} initialStationId={typeof focused==='number'?focused:undefined}/>}
   {tab==='master'&&<MasterPanel user={user} defs={defs} feeders={feeders} reloadDefinitions={reload} readonly={!onUnit} initialSearch={typeof focused==='string'?focused:undefined}/>}
   {tab==='visits'&&<VisitList defs={defs} feeders={feeders} readonly={readonly||!onUnit} canVerify={canVerify}/>}
   {tab==='settings'&&user.role==='admin'&&<DefinitionSettings defs={defs} reload={reload}/>}
   {tab==='formulas'&&<FormulaSettings admin={user.role==='admin'}/>}
   {tab==='map'&&<MapPage admin={user.role==='admin'} canInput={!readonly&&onUnit} onNavigate={navigate}/>}
   {tab==='work'&&<WorkList canEdit={!readonly&&onUnit} onOpenStation={code=>navigate('analysis',code)}/>}
   {tab==='monitor'&&<MonitoringPage canInput={!readonly&&onUnit} onNavigate={navigate}/>}
   {tab==='export'&&<ExportPage admin={user.role==='admin'} userId={user.id}/>}
   {tab==='analysis'&&<AnalysisPage admin={user.role==='admin'} userId={user.id} canInput={!readonly&&onUnit} onNavigate={navigate}/>}</>):<p>Memuat definisi pengukuran...</p>}
 </div>
}
