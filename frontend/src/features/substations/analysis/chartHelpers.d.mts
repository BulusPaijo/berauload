export function feederStacks(summary:{feeder_categories:{feeder_id:number|null;category:string;count:number}[]},defs:{feeders:{id:number;name:string}[]}):Record<string,string|number>[];
export function scatterPairs(points:{id:number;sessions:Record<string,number|null>}[],sessions:string[]):{id:number;x:number;y:number}[];
export function findingPareto(findings:{code:string;name:string;count:number;color:string}[]):{code:string;name:string;count:number;color:string}[];
export function trendRows(points:{day:string;session:string;value:number}[]):Record<string,string|number>[];
export function encodeCsv(rows:object[]):string;
export function densityKey(userId:number):string;
export function readDensity(storage:{getItem:(key:string)=>string|null},userId:number):'compact'|'comfortable';
export function saveDensity(storage:{setItem:(key:string,value:string)=>void},userId:number,value:string):void;
