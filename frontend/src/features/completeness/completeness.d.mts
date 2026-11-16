export type DayCell={day:string;filled_hours:number;expected_hours:number;status:'draft'|'verified'|'final';future:boolean};
export type Summary={filled_hours:number;expected_hours:number;percent:number|null;final_days:number};
export declare function basisLabel(basis:'system.load'|'any_input'):string;
export declare function statusLetter(status:string):string;
export declare function cellLabel(cell:DayCell):string;
export declare function coverageLabel(summary:Summary):string;
export declare function initialRange(today:string):[string,string];
