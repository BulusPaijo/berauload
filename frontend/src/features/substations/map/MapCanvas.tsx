import {useEffect,useRef,useState} from 'react';
import * as L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type {MapPoint,TileSettings} from './types';
import {clusterPoints,colorAndShape,escapeText,quartiles} from './helpers.mjs';
import './map.css';

type Props={points:MapPoint[];rules:{code:string;kind:string;group_name:string;color:string;marker?:string}[];
 colorMode:string;group:string;tiles:TileSettings|null;onSelect:(point:MapPoint)=>void;locate:number[]|null};
export default function MapCanvas({points,rules,colorMode,group,tiles,onSelect,locate}:Props){
 const container=useRef<HTMLDivElement>(null),map=useRef<L.Map|null>(null);
 const markerLayer=useRef<L.LayerGroup|null>(null),tileLayer=useRef<L.TileLayer|null>(null);
 const [tileFailed,setTileFailed]=useState(false);
 const latest=useRef({points,rules,colorMode,group,onSelect});
 latest.current={points,rules,colorMode,group,onSelect};
 useEffect(()=>{
  if(!container.current||map.current)return;
  const instance=L.map(container.current,{zoomControl:true,preferCanvas:true}).setView([0,0],2);
  map.current=instance;markerLayer.current=L.layerGroup().addTo(instance);
  L.control.scale({imperial:false}).addTo(instance);
  const update=()=>{
   const data=latest.current,layer=markerLayer.current;if(!layer)return;
   layer.clearLayers();
   const pointValue=(p:MapPoint)=>data.colorMode==='umur'?p.age_days:
    data.colorMode.startsWith('column:')?p.columns?.[data.colorMode.slice(7)]?.value:null;
   const breaks=quartiles(data.points.map(pointValue));
   const groups=clusterPoints(data.points,(lat:number,lon:number)=>instance.project([lat,lon],instance.getZoom()),54);
   for(const item of groups){
    if(item.members.length>1){
     const badge=L.divIcon({className:'gardu-map-marker',html:`<span class="gardu-map-cluster">${item.members.length}</span>`,iconSize:[36,36],iconAnchor:[18,18]});
     L.marker([item.lat,item.lon],{icon:badge}).on('click',()=>instance.setView([item.lat,item.lon],Math.min(18,instance.getZoom()+2))).addTo(layer);
    }else{
     const p=item.members[0];const style=colorAndShape(p,data.colorMode,data.group,data.rules,breaks);
     const marker=L.divIcon({className:'gardu-map-marker',html:`<span class="gardu-shape gardu-${escapeText(style.marker)}" style="--pin:${escapeText(style.color)}"></span>`,iconSize:[30,30],iconAnchor:[15,15]});
     L.marker([p.lat,p.lon],{icon:marker,title:p.code}).on('click',()=>data.onSelect(p)).addTo(layer);
    }
   }
  };
  instance.on('moveend zoomend',update);
  return()=>{instance.off('moveend zoomend',update);instance.remove();map.current=null;markerLayer.current=null;tileLayer.current=null};
 },[]);
 useEffect(()=>{
  const instance=map.current;if(!instance)return;
  markerLayer.current?.clearLayers();
  if(points.length){
   const bounds=L.latLngBounds(points.map(p=>[p.lat,p.lon] as L.LatLngTuple));
   if(bounds.isValid())instance.fitBounds(bounds.pad(.12),{maxZoom:14});
  }
  instance.fire('moveend');
 },[points]);
 useEffect(()=>{map.current?.fire('moveend');},[colorMode,group,rules]);
 useEffect(()=>{
  const instance=map.current;if(!instance)return;
  if(tileLayer.current){instance.removeLayer(tileLayer.current);tileLayer.current=null;}
  setTileFailed(false);
  if(!tiles?.enabled)return;
  const attribution=tiles.tile_url.includes('openstreetmap.org')?
   '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors':escapeText(tiles.attribution);
  const layer=L.tileLayer(tiles.tile_url,{attribution,maxZoom:19});
  layer.on('tileerror',()=>setTileFailed(true));layer.addTo(instance);tileLayer.current=layer;
 },[tiles]);
 useEffect(()=>{if(locate&&map.current)map.current.setView([locate[0],locate[1]],14);},[locate]);
 return <div className="gardu-map-stage"><div className="gardu-map-canvas" ref={container} aria-label="Peta titik gardu distribusi" role="application"/>
  {(!tiles?.enabled||tileFailed)&&<div role="status" className="gardu-map-tile-message">{!tiles?.enabled?'Ubin dimatikan admin. Titik gardu tetap ditampilkan.':'Ubin peta tidak dapat dimuat. Titik dan skala tetap tersedia.'}</div>}</div>;
}
