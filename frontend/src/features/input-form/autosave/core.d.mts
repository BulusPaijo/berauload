export const MAX_BACKUP_BYTES:number;
export const BACKUP_AGE_MS:number;
export function backupKey(userId:number,unitId:number,day:string):string;
export function parseCell(raw:string):number|null;
export type Backup={schema:1;changedAt:number;drafts:Record<string,string>;base:Record<string,number|null>};
export function saveBackup(storage:Storage|null,key:string,drafts:Record<string,string>,base:Record<string,number|null>,changedAt?:number):boolean;
export function readBackup(storage:Storage|null,key:string,now?:number):Backup|null;
export function shouldHeartbeat(lastActivity:number,dirty:boolean,now:number):boolean;
export function sessionRemaining(expiresAt:string,now?:number):number;
export function showExpiryBanner(expiresAt:string,now?:number):boolean;
export const pause:(ms:number)=>Promise<void>;
export class HourQueue {
  paused:boolean;
  constructor(send:(hour:number)=>Promise<void>,onStatus?:(hour:number,status:string)=>void,delay?:number,sleep?:(ms:number)=>Promise<void>);
  mark(hour:number):void;
  flush(hour:number):Promise<void>|null;
  flushAll():Promise<void>;
  resolve(hour:number):Promise<void>|null;
  resume():Promise<void>;
  stop():void;
}
