export type UnitNode={id:number;code:string;name:string;level:'up3'|'ulp'|'kp';parent_id:number|null;active:boolean;legacy_home?:boolean;roles?:string[];children:UnitNode[]};
export function flattenUnits(tree:UnitNode[]):UnitNode[];
export function pickUnit(tree:UnitNode[],saved:number|null):UnitNode|null;
export function canWrite(unit:UnitNode|null,globalRole:string):boolean;
export function isRootOnly(unit:UnitNode|null):boolean;
export function cacheUnitKey(userId:number,unitId:number,key:string):string;
export function viewModeLabel(unit:UnitNode|null,role:string):string|null;
export function rootDataHint(unit:UnitNode|null):string|null;
