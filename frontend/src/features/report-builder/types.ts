export type ReportKind='heading'|'text'|'stat'|'chart'|'table';
export type ReportBlock={
  id:string;kind:ReportKind;title:string;text:string;metric_codes:string[];
  aggregation:'avg'|'min'|'peak';granularity:'hour'|'day'|'month';
};
export type ReportTemplate={id:number;name:string;description:string;scope:'system'|'personal';
  owner_id:number;blocks:ReportBlock[];version:number;archived:boolean};
import type {Status} from '../unit-references/SourceStatus';
export type ReportResult={source_status?:Status;start:string;end:string;readings_available:number;time_zone:string;
  blocks:({id:string;kind:ReportKind;title:string;text:string;unit:string;metric_codes:string[];
    value?:number|null;count?:number;rows?:({period:string;[metric:string]:string|number|null})[]})[]};
export const newBlock=(kind:ReportKind):ReportBlock=>({
  id:`block-${Date.now()}-${Math.random().toString(36).slice(2,7)}`,
  kind,title:({heading:'Judul Bagian',text:'Catatan',stat:'Indikator',chart:'Grafik',table:'Tabel'} as Record<ReportKind,string>)[kind],
  text:'',metric_codes:[],aggregation:'avg',granularity:'day'
});
