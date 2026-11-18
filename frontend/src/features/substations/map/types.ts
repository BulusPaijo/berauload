import type {AnalysisRow,Summary} from '../analysis/types';
export type MapPoint=Pick<AnalysisRow,'id'|'code'|'name'|'power_kva'|'feeder'|'measurement_id'|'age_days'|'status'|'reference'|'columns'> & {lat:number;lon:number;unit_id:number;finding_codes:string[];findings?:AnalysisRow['findings'];category:{code:string;name?:string;color?:string;marker?:string};categories?:{code:string;group_name:string}[]};
export type TileSettings={id?:number;enabled:boolean;tile_url:string;attribution:string};
export type MapResponse={points:MapPoint[];total:number;missing_coordinates:number;missing:{id:number;code:string;name:string}[];
 missing_truncated:boolean;summary:Summary;finding_counts_on_map:Record<string,number>};
