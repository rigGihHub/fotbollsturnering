export const ADMIN_DRAFT_PREFIX = 'cupnavi_admin_draft_v1:';
const VENUE_WINDOW_ARCHIVE_PREFIX = 'cupnavi_venue_window_archive_v1:';
export function readVenueWindowArchive<T>(cupId:number):T[] {
  try { const rows=JSON.parse(sessionStorage.getItem(VENUE_WINDOW_ARCHIVE_PREFIX+cupId)||'[]'); return Array.isArray(rows)?rows:[]; }
  catch { return []; }
}
export function writeVenueWindowArchive<T>(cupId:number,rows:T[]):boolean {
  try {
    const key=VENUE_WINDOW_ARCHIVE_PREFIX+cupId;
    if(rows.length)sessionStorage.setItem(key,JSON.stringify(rows));else sessionStorage.removeItem(key);
    return true;
  } catch { return false; }
}
export function restoreVenueWindowArchive<T extends {pitch_number:number;play_date:string}>(current:T[],archived:T[]):T[] {
  const restoredGroups=new Set(archived.map(row=>`${row.pitch_number}:${row.play_date}`));
  return [...current.filter(row=>!restoredGroups.has(`${row.pitch_number}:${row.play_date}`)),...archived];
}
export type Draft<T> = { saved:T; data:T; updatedAt:number };
export function restoreDraft<T extends object>(server:T, draft:Draft<T>|null):T {
  if(!draft || Date.now()-draft.updatedAt>24*60*60*1000)return server;
  const restored={...server};
  for(const key of Object.keys(draft.data) as (keyof T)[]) {
    // Only user edits are restored; current server metadata stays current.
    if(JSON.stringify(draft.data[key])!==JSON.stringify(draft.saved[key]))restored[key]=draft.data[key];
  }
  return restored;
}
export function readAdminDraft<T extends object>(key:string, server:T):T {
  try { return restoreDraft(server,JSON.parse(sessionStorage.getItem(ADMIN_DRAFT_PREFIX+key)||'null')); }
  catch { return server; }
}
export function writeAdminDraft<T>(key:string,saved:T,data:T) {
  try {
    if(JSON.stringify(saved)===JSON.stringify(data))sessionStorage.removeItem(ADMIN_DRAFT_PREFIX+key);
    else sessionStorage.setItem(ADMIN_DRAFT_PREFIX+key,JSON.stringify({saved,data,updatedAt:Date.now()}));
  } catch { /* Navigation guards still protect unsaved work if storage is full. */ }
  if(typeof window!=='undefined')window.dispatchEvent(new Event('cupnavi:admin-draft-updated'));
}
export function clearAdminDrafts() {
  try { for(const key of Object.keys(sessionStorage))if(key.startsWith(ADMIN_DRAFT_PREFIX)||key.startsWith(VENUE_WINDOW_ARCHIVE_PREFIX))sessionStorage.removeItem(key); } catch {}
  if(typeof window!=='undefined')window.dispatchEvent(new Event('cupnavi:admin-draft-updated'));
}
export function matchTiming(rules:{halves:number;minutes_per_half:number;halftime_minutes:number;pitch_break_minutes:number}) {
  const pauseCount=Math.max(0,rules.halves-1);
  const pauses=pauseCount*rules.halftime_minutes;
  const duration=rules.halves*rules.minutes_per_half+pauses;
  return {duration,slot:duration+rules.pitch_break_minutes,pauseCount,pauses};
}
export function mergeVenueRows<T extends {dates?:string[];pitches:Array<{pitch_number:number}>;windows:Array<{pitch_number:number;play_date:string}>}>(draft:T,server:T):T {
  const surviving=new Set(server.pitches.map(p=>p.pitch_number));
  const dates=new Set(server.dates??server.windows.map(w=>w.play_date));
  const groups=new Set(draft.windows.filter(w=>surviving.has(w.pitch_number)&&dates.has(w.play_date)).map(w=>`${w.pitch_number}:${w.play_date}`));
  return {...server,
    pitches:server.pitches.map(p=>draft.pitches.find(old=>old.pitch_number===p.pitch_number)||p),
    windows:[...server.windows.filter(w=>dates.has(w.play_date)&&!groups.has(`${w.pitch_number}:${w.play_date}`)),...draft.windows.filter(w=>surviving.has(w.pitch_number)&&dates.has(w.play_date))],
  };
}
