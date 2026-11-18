export type ComparedCell = {key:string;code:string;label:string;line:number;mine:string;server:string};
export function conflictCells(drafts:Record<string,string>, id:number, serverValues:Array<{param_id:number;line_no:number;value:number|null;flag:string|null}>, parameters:Array<{id:number;code:string;name:string}>):ComparedCell[];
