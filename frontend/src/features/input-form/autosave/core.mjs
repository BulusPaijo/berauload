/** Pure autosave queue and local recovery helpers (no React dependency). */
export const MAX_BACKUP_BYTES = 250_000;
export const BACKUP_AGE_MS = 7 * 24 * 60 * 60 * 1000;
export const backupKey = (userId, unitId, day) =>
  `berauload:input:v1:user:${userId}:unit:${unitId}:day:${day}`;
export const parseCell = raw => {
  const value = raw.trim();
  if (!value) return null;
  const normalized = value.includes(',') && value.includes('.')
    ? value.replace(/\./g, '').replace(',', '.') : value.replace(',', '.');
  const number = Number(normalized);
  if (!Number.isFinite(number)) throw new Error(`Nilai bukan angka: ${raw}`);
  return number;
};
export function saveBackup(storage, key, drafts, base, changedAt = Date.now()) {
  try {
    if (!Object.keys(drafts).length) { storage?.removeItem(key); return true; }
    const payload = JSON.stringify({schema:1, changedAt, drafts, base});
    if (payload.length > MAX_BACKUP_BYTES) return false;
    storage?.setItem(key, payload);
    return true;
  } catch { return false; }
}
export function readBackup(storage, key, now = Date.now()) {
  try {
    const raw = storage?.getItem(key);
    if (!raw || raw.length > MAX_BACKUP_BYTES) return null;
    const data = JSON.parse(raw);
    if (data.schema !== 1 || typeof data.changedAt !== 'number'
      || data.changedAt > now || now-data.changedAt > BACKUP_AGE_MS
      || !data.drafts || typeof data.drafts !== 'object'
      || Array.isArray(data.drafts) || !data.base || typeof data.base !== 'object') return null;
    if (Object.values(data.drafts).some(v => typeof v !== 'string')) return null;
    return data;
  } catch { return null; }
}
export const shouldHeartbeat = (lastActivity, dirty, now) =>
  Boolean(dirty || now-lastActivity <= 30 * 60 * 1000);
export const sessionRemaining = (expiresAt, now=Date.now()) =>
  Math.max(0, new Date(expiresAt).getTime()-now);
export const showExpiryBanner = (expiresAt, now=Date.now()) =>
  sessionRemaining(expiresAt, now) < 10 * 60 * 1000;
export const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

export class HourQueue {
  constructor(send, onStatus=()=>{}, delay=3000, sleep=pause) {
    this.send=send;this.onStatus=onStatus;this.delay=delay;this.sleep=sleep;
    this.hours=new Map();this.paused=false;
  }
  entry(hour) {
    if (!this.hours.has(hour)) this.hours.set(hour,
      {dirty:false, running:false, blocked:false, timer:null, promise:null});
    return this.hours.get(hour);
  }
  mark(hour) {
    const row=this.entry(hour);row.dirty=true;
    this.onStatus(hour,'belum disimpan');
    if (row.timer) clearTimeout(row.timer);
    if (!this.paused && !row.blocked)
      row.timer=setTimeout(()=>{row.timer=null;void this.flush(hour)},this.delay);
  }
  async flush(hour) {
    const row=this.entry(hour);
    if (row.timer) {clearTimeout(row.timer);row.timer=null;}
    if (this.paused || row.blocked || row.running || !row.dirty) return row.promise;
    row.running=true;
    row.promise=(async()=>{
      while (row.dirty && !row.blocked && !this.paused) {
        row.dirty=false;this.onStatus(hour,'menyimpan');
        let status='gagal';
        for (let attempt=0;attempt<=3;attempt++) {
          try { await this.send(hour);status='ok';break; }
          catch (error) {
            const code=error?.status||0;
            if (code===401) {this.paused=true;status='session';break;}
            if (code===409) {row.blocked=true;status='conflict';break;}
            if (code>=400 && code<500) break;
            if (attempt===3) break;
            await this.sleep(500 * 2**attempt);
          }
        }
        if (status==='ok') this.onStatus(hour,'tersimpan');
        else {
          row.dirty=true;
          this.onStatus(hour,status==='session'?'sesi berakhir':status==='conflict'?'ada konflik':'gagal menyimpan');
          break;
        }
      }
    })().finally(()=>{row.running=false;row.promise=null});
    return row.promise;
  }
  async flushAll() {await Promise.all([...this.hours.keys()].map(h=>this.flush(h)));}
  resolve(hour) {const row=this.entry(hour);row.blocked=false;row.dirty=true;return this.flush(hour);}
  resume() {this.paused=false;return this.flushAll();}
  stop() {for(const row of this.hours.values())if(row.timer) clearTimeout(row.timer);}
}
