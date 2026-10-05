const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const ts=require('typescript');
function moduleAt(file,storage){const context={exports:{},Date,sessionStorage:storage};vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(__dirname,'..',file),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,context);return context.exports;}
const rows=new Map();const storage={getItem:k=>rows.get(k)||null,setItem:(k,v)=>rows.set(k,v),removeItem:k=>rows.delete(k)};
const {restoreDraft,readAdminDraft,writeAdminDraft,mergeVenueRows,matchTiming,readVenueWindowArchive,writeVenueWindowArchive}=moduleAt('src/lib/admin-draft.ts',storage);
const base={name:'Plan 1',scheduled_count:1};const draft={...base,name:'Huvudplan'};
writeAdminDraft('1:venues',base,draft);
assert.equal(readAdminDraft('1:venues',{...base,scheduled_count:3}).name,'Huvudplan');
assert.equal(readAdminDraft('1:venues',{...base,scheduled_count:3}).scheduled_count,3);
assert.equal(readAdminDraft('2:venues',base).name,'Plan 1');
writeAdminDraft('1:venues',draft,draft);assert.equal(rows.size,0);
assert.equal(restoreDraft(base,{saved:base,data:draft,updatedAt:Date.now()-90000000}).name,'Plan 1');
const venueDraft={pitches:[{pitch_number:1,name:'A edited'},{pitch_number:2,name:'B edited'}],windows:[{pitch_number:1,play_date:'2026-10-04',start_time:'10:00',end_time:'11:00'},{pitch_number:1,play_date:'2026-10-04',start_time:'12:00',end_time:'13:00'},{pitch_number:2,play_date:'2026-10-04',start_time:'10:00',end_time:'14:00'}]};
const server={pitches:[{pitch_number:1,name:'A'},{pitch_number:2,name:'B'},{pitch_number:3,name:'C'}],windows:[1,2,3].map(pitch_number=>({pitch_number,play_date:'2026-10-04',start_time:'09:00',end_time:'18:00'}))};
const merged=mergeVenueRows(venueDraft,server);assert.equal(merged.pitches[1].name,'B edited');assert.equal(merged.pitches[2].name,'C');assert.equal(merged.windows.filter(w=>w.pitch_number===1).length,2);assert.equal(merged.windows.find(w=>w.pitch_number===2).start_time,'10:00');assert.equal(merged.windows.find(w=>w.pitch_number===3).start_time,'09:00');
assert.equal(server.pitches[1].name,'B');
const shortened={...server,dates:['2026-10-04'],windows:[...server.windows,{pitch_number:1,play_date:'2026-10-05',start_time:'09:00',end_time:'18:00'}]};
const oldDraft={...venueDraft,windows:[...venueDraft.windows,{pitch_number:1,play_date:'2026-10-05',start_time:'11:00',end_time:'12:00'}]};
const currentRows=mergeVenueRows(oldDraft,shortened);
// Current server metadata is authoritative even if older persisted rows exist.
// The caller surfaces non-current draft rows separately before excluding them.
assert.equal(currentRows.windows.filter(w=>w.play_date==='2026-10-04'&&w.pitch_number===1).length,2);
assert.equal(currentRows.windows.filter(w=>w.play_date==='2026-10-05'&&w.start_time==='11:00').length,0);
assert.equal(currentRows.windows.filter(w=>w.play_date==='2026-10-05').length,0);
assert.equal(writeVenueWindowArchive(10,oldDraft.windows),true);
assert.equal(readVenueWindowArchive(10).length,4);
assert.equal(readVenueWindowArchive(11).length,0);
assert.equal(moduleAt('src/lib/admin-draft.ts',storage).readVenueWindowArchive(10).length,4,'Archive survives component/step reload');
writeVenueWindowArchive(10,[]);assert.equal(readVenueWindowArchive(10).length,0);
for(const [halves,minutes_per_half,halftime_minutes,pitch_break_minutes,duration,slot] of [[2,15,5,5,35,40],[1,20,5,0,20,20],[4,10,0,5,40,45],[4,10,5,5,55,60]]) {const actual=matchTiming({halves,minutes_per_half,halftime_minutes,pitch_break_minutes});assert.equal(actual.duration,duration);assert.equal(actual.slot,slot);}
const nav=moduleAt('src/lib/admin-navigation.ts');for(const [id] of [...nav.adminFlowSteps,...nav.adminToolSteps])assert.equal(nav.parseAdminStep('#'+id),id);assert.equal(nav.parseAdminStep('#unknown'),'overview');
console.log('Admin draft retention, new pitch rows, timing and all navigation targets: PASS');
