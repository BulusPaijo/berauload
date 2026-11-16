export function rankRows(codes:string[],values:Record<string,number|null>|undefined,units:Record<string,string>|undefined):{
 rows:{code:string,value:number}[];mixed:boolean};
export function availableCount(codes:string[],values:Record<string,number|null>|undefined):number;
export function sparkSegments(points:{hour:number,value:number|null}[]|undefined,width?:number,height?:number):number[][][];
