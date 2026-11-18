export function phaseTone(pct:number|null):string;
export function phaseBars(byCode:Record<string,{value:number|null}>,codes?:string[],nominalCode?:string):{code:string;letter:string;value:number|null;pct:number|null;tone:string}[];
export function lineTable(params:{id:number;name:string;scope:string;unit:string;active:boolean;display_order:number}[],values:{param_id:number;line_no:number;value:number|null;flag:string|null}[],unit?:string):{head:string[];rows:{line:number;cells:(number|string|null)[]}[]};
export function trendRows(trend:{day:string;session:string;value:number}[]):{sessions:string[];rows:Record<string,string|number>[]};
export function mapsLink(lat:number|null|undefined,lon:number|null|undefined):string|null;
export function followTone(status:string):string;
