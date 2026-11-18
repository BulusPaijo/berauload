export type Filters=Record<string,string|string[]> & {findings:string[]};
export declare const defaults:Record<string,string>;
export declare const defaultColumns:string[];
export declare function fromQuery(search:string):Filters;
export declare function toQuery(state:Record<string,unknown>):string;
export declare function chips(rules:Array<Record<string,unknown>>):Array<{code:string;name:string;kind:string;color:string;group:string}>;
export declare function valueText(value:number|null|undefined,digits?:number,incomplete?:boolean):string;
export declare function direction(state:Filters,key:string):Record<string,string>;
export declare function applyView(view:{layout:Record<string,unknown>},definitions?:{
  columns:Array<{code:string;active:boolean}>;
  fields:Array<{code:string;active:boolean}>;
  rules:Array<{code:string;kind:string;active:boolean}>;
}):Filters;
export declare function serializeView(state:Filters,columns:string[],widths:Record<string,number>):Record<string,unknown>;
export function designColumns(definitions:{columns:{code:string;active:boolean}[];sessions:{code:string}[]}|null|undefined):string[];
export function findingColumns(rules:{code:string;kind:string;active:boolean;expression:string}[]):Record<string,string[]>;
