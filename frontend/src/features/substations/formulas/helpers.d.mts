export type ColumnOrigin = {origin:string;expression:string;default_expression?:string|null};
export declare function originLabel(row:ColumnOrigin):string;
export declare function insertToken(text:string, token:string, start:number, end:number):{value:string;caret:number};
export declare function displayValue(value:number|null|undefined, digits?:number, incomplete?:boolean):string;
export declare function errorMessage(reason:unknown):string;

export declare function recalcDecision(status:{busy?:boolean;remaining:number;processed?:number}):'retry'|'stop'|'continue';
export declare function orderedCodes(rows:{code:string;display_order:number;id:number}[],code:string,delta:number):string[];
export declare function dragCodes(rows:{code:string;display_order:number;id:number}[],from:string,to:string):string[];
