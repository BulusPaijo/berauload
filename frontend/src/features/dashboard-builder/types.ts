import type {Catalog} from '../../api';
import type {Status} from '../unit-references/SourceStatus';

export type PanelKind='line'|'area'|'bar'|'stat'|'gauge'|'table'|'rule'|'step'|'stacked_bar';
export type PanelSource='metric'|'historical'|'engineering';
export type Aggregation='avg'|'min'|'peak';
import type {UnitItem} from '../units/UnitManager';
export type LegendPosition='bottom'|'top'|'right'|'hidden';
export type DashPanel={
  id:string;title:string;kind:PanelKind;source:PanelSource;
  metric_codes:string[];source_id:number|null;aggregation:Aggregation;w:number;h:number;
  style_preset?:'classic'|'dark'|'soft';font_family?:'system'|'mono';
  title_font_size?:number;value_font_size?:number;text_color?:string|null;background_color?:string|null;border_color?:string|null;
  legend?:LegendPosition;decimals?:number;display_unit?:string|null;colors?:Record<string,string>;show_points?:boolean;
};
export type DashLayout={
  id:number;name:string;description:string;scope:'system'|'personal';owner_id:number;
  panels:DashPanel[];version:number;is_default:boolean;archived:boolean;
};
export type LayoutList={items:DashLayout[];effective_default_id:number|null;system_default_id:number|null;personal_default_id:number|null};
export type HistoricalOption={id:number;name:string;unit:string;archived:boolean};
export type RuleOption={id:number;name:string;status:string};
export type DataPoint={period:string;[key:string]:string|number|null};
export type LoadedPanel={points:DataPoint[];series:{key:string;name:string;unit:string}[];unit:string;
  coverage?:string;sourceStatus?:Status;error?:string;rule?:{status_counts:Record<string,number>;missing_or_invalid_hours:number;valid_hours:number;expected_hours:number};};
export type PaneContext={start:string;end:string;granularity:'hour'|'day'|'month'|'year';catalog:Catalog;units?:UnitItem[]};
// The caller resolves both primary roles from catalog.roles; never hard-code codes.
export const defaultPanel=(loadCode:string):DashPanel=>({
  id:`panel-${Math.random().toString(36).slice(2,11)}`,title:'Grafik Beban Sistem',
  kind:'line',source:'metric',metric_codes:loadCode?[loadCode]:[],source_id:null,
  aggregation:'avg',w:6,h:2,style_preset:'classic',font_family:'system',title_font_size:13,value_font_size:32,legend:'bottom',decimals:2,display_unit:null,colors:{},show_points:false,
});
