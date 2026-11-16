import test from 'node:test';
import assert from 'node:assert/strict';
import {HourQueue,backupKey,readBackup,saveBackup,parseCell,shouldHeartbeat,
  showExpiryBanner} from '../src/features/input-form/autosave/core.mjs';

test('backup isolates user/unit/day, tolerates unavailable storage, expires',()=>{
 const mem=new Map();const storage={setItem:(k,v)=>mem.set(k,v),getItem:k=>mem.get(k),removeItem:k=>mem.delete(k)};
 const a=backupKey(1,2,'2026-11-16');const b=backupKey(2,2,'2026-11-16');
 assert.notEqual(a,b);
 assert.equal(saveBackup(storage,a,{'3:load':'0'},{'3:load':null},100),true);
 assert.equal(readBackup(storage,a,120).drafts['3:load'],'0');
 assert.equal(readBackup(storage,b,120),null);
 assert.equal(readBackup(storage,a,100+8*24*3600*1000),null);
 mem.set(a,'not-json');assert.equal(readBackup(storage,a,120),null);
 assert.equal(saveBackup({setItem(){throw Error('private')},getItem(){throw Error('private')}},a,{'1:a':'2'},{},120),false);
});

test('empty is null, numeric zero remains zero',()=>{
 assert.equal(parseCell(''),null);assert.equal(parseCell('0'),0);assert.equal(parseCell('1,25'),1.25);
});

test('one request per hour at a time, later edits form next wave',async()=>{
 let resolveFirst;let active=0;let max=0;let calls=0;
 const q=new HourQueue(async()=>{calls++;active++;max=Math.max(max,active);
   if(calls===1)await new Promise(r=>{resolveFirst=r});active--;},()=>{},9999);
 q.mark(3);const first=q.flush(3);q.mark(3);const second=q.flush(3);
 assert.equal(calls,1);resolveFirst();await Promise.all([first,second]);
 assert.equal(calls,2);assert.equal(max,1);q.stop();
});

test('retry only network/5xx, pause on 401 and 409, resume after login',async()=>{
 let tries=0;const q=new HourQueue(async()=>{tries++;if(tries<4)throw {status:503}},()=>{},9999,async()=>{});
 q.mark(2);await q.flush(2);assert.equal(tries,4);
 let code=401;const other=new HourQueue(async()=>{if(code)throw {status:code}},()=>{},9999,async()=>{});
 other.mark(0);await other.flush(0);assert.equal(other.paused,true);
 code=0;await other.resume();assert.equal(other.paused,false);
 const conflict=new HourQueue(async()=>{throw {status:409}},()=>{},9999,async()=>{});
 conflict.mark(1);await conflict.flush(1);assert.equal(conflict.entry(1).blocked,true);conflict.stop();
 let forbidden=0;const four=new HourQueue(async()=>{forbidden++;throw {status:422}},()=>{},9999,async()=>{});
 four.mark(9);await four.flush(9);assert.equal(forbidden,1);four.stop();
});

test('heartbeat and session warning use activity/dirty state',()=>{
 const t=Date.parse('2026-11-16T00:00:00Z');
 assert.equal(shouldHeartbeat(t-31*60000,false,t),false);
 assert.equal(shouldHeartbeat(t-31*60000,true,t),true);
 assert.equal(showExpiryBanner(new Date(t+9*60000).toISOString(),t),true);
 assert.equal(showExpiryBanner(new Date(t+11*60000).toISOString(),t),false);
});
