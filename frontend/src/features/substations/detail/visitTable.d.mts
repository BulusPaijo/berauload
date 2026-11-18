import type {GarduTone} from '../grid.mjs';
type P={id:number;code:string;name:string;scope:string;unit:string;active:boolean;display_order:number};
type V={param_id:number;line_no:number;value:number|null;flag:string|null};
export type Changed={param_id:number;line_no:number;before:number|null;before_flag:string|null};
export type TCell={id:number;value:number|null;flag:string|null;changed:boolean;before:number|null;beforeFlag:string|null};
export type HistoryChange={param_id:number;code:string;name:string;unit:string;line_no:number;before:number|null;before_flag:string|null;after:number|null;after_flag:string|null};
export type HistoryEntry={id:number;at:string;user:string;kind:string;actor_role:string|null;reason:string|null;
 revision_before:number|null;revision_after:number|null;summary:string;changes:HistoryChange[];meta:{field:string;label:string;before:unknown;after:unknown}[]};
export declare const fmtValue:(value:number|null|undefined,flag:string|null|undefined,flagName?:(f:string)=>string)=>string;
export declare function visitTable(params:P[],values:V[],lineCount:number,lineLabels?:string[],changed?:Changed[]):{
 head:{title:string;unit:string;cols:{id:number;code:string;sub:string;phase:string}[]}[];
 rows:{line:number;label:string;cells:TCell[]}[];
 gardu:{title:string;tone:GarduTone;unit:string;cells:(TCell&{code:string;sub:string;phase:string})[]}[];
 changedCount:number};
export declare function describeChange(c:HistoryChange,flagName?:(f:string)=>string,lineLabels?:string[]):string;
export declare const KIND_TONE:Record<string,string>;
export declare function historyView(entries:HistoryEntry[],flagName?:(f:string)=>string,lineLabels?:string[]):{
 id:number;at:string;user:string;tone:string;summary:string;revision:number|null;reason:string;lines:string[];count:number}[];
export declare const stateLabel:(s:string)=>string;
export declare const whenLabel:(iso:string|null|undefined)=>string;
