export type FormTab = {code:string;name:string;active:boolean;display_order:number};
export type FormPlacement = {metric_code:string;tab_code:string;display_order:number;visible:boolean};
export type InputFormConfig = {version:number;tabs:FormTab[];placements:FormPlacement[]};
export const DEFAULT_TABS:FormTab[] = [
  {code:'PEMBANGKIT',name:'Pembangkit',active:true,display_order:0},
  {code:'KUALITAS',name:'Frekuensi & Tegangan',active:true,display_order:1},
  {code:'FEEDER',name:'Arus Feeder',active:true,display_order:2},
  {code:'REKAP',name:'Rekap Sistem',active:true,display_order:3},
  {code:'REKAP_LAIN',name:'Kolom Rekap Tambahan',active:true,display_order:4},
];
