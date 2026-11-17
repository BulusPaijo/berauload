import {useEffect,useState} from 'react';
import {Activity} from 'lucide-react';
import {useBranding} from './BrandingContext';
export default function BrandMark({login=false}:{login?:boolean}){
 const {branding}=useBranding();
 const [failed,setFailed]=useState(false);
 useEffect(()=>setFailed(false),[branding.logo_version,branding.has_logo]);
 return <div className={login?'login-logo':'brand-icon'}>
  {branding.has_logo&&!failed?<img alt={branding.app_name} className="brand-mark-image"
   src={`/api/branding/logo?v=${branding.logo_version}`} onError={()=>setFailed(true)}/>
  :<Activity size={login?33:26} aria-label={branding.app_name}/>}
 </div>
}
