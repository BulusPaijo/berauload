let lastActive = Date.now();
let pending = false;
export function markActive() {lastActive=Date.now();}
export function setDirty(value) {pending=Boolean(value);}
export function hasDirty() {return pending;}
export function activityAt() {return lastActive;}
