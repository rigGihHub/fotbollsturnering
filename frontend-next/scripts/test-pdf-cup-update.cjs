const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ts=require("typescript");
function load(file){
 const moduleRef={exports:{}};
 const source=fs.readFileSync(path.join(__dirname,"../src",file),"utf8");
 const code=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2020,module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}}).outputText;
 vm.runInNewContext(code,{exports:moduleRef.exports,module:moduleRef,Date,require:name=>name.endsWith(".css")?{default:{}}:require(name)});
 return moduleRef.exports;
}
const {reviewScheduleRevision}=load("lib/schedule-revision-review.ts");
const schedule={start_date:"2026-10-24",end_date:"2026-10-24",matches:[{id:7,home_label:"Örebro SK",away_label:"AIK",scheduled_start:"2026-10-24T09:00:00",pitch_number:1,played:false,schedule_locked:false}]};
const pitches=[{pitch_number:1,name:"Sörbyvallen"},{pitch_number:2,name:"Ekäng"}];
const row={home_team:" Örebro  SK ",away_team:"aik",time:"10.15",venue:"ekäng"};
const review=(rows=[row],current=schedule,venues=pitches)=>reviewScheduleRevision({matches:rows},current,venues);
assert.equal(review().changes[0].nextStart,"2026-10-24T10:15");
assert.equal(review().changes[0].match.id,7);
assert.equal(review().changes[0].nextPitch,2);
assert.equal(review([{...row,time:"09:00",venue:"Sörbyvallen"}]).unchanged,1);
assert.equal(review([row,row]).changes.length,0,"Duplicated PDF rows must not create two conflicting writes");
assert.equal(review([row,row]).unmatched.length,1);
const reversed=review([{...row,home_team:"AIK",away_team:"Örebro SK"}]);
assert.equal(reversed.changes.length,1);
assert.equal(reversed.changes[0].match.home_label,"Örebro SK","PDF ordering must never change the cup's home/away assignments");
assert.match(reversed.changes[0].matchingNote,/hemma\/borta behålls/);
assert.equal(review([row,{...row,home_team:"AIK",away_team:"Örebro SK"}]).changes.length,0,"Opposite ordering must still count as a duplicated PDF row");
assert.equal(review([row],{...schedule,matches:[...schedule.matches,{...schedule.matches[0],id:8}]}).changes.length,0);
assert.equal(review([row],{...schedule,end_date:"2026-10-25"}).changes.length,0);
assert.equal(review([{...row,time:"2026-10-25T10:15"}],{...schedule,end_date:"2026-10-25"}).changes.length,1);
assert.equal(review([{...row,time:"2026-02-30T10:15"}],{...schedule,start_date:"2026-01-01",end_date:"2026-12-31"}).changes.length,0);
assert.equal(review([{...row,time:"25:00"}]).changes.length,0);
assert.equal(review([{...row,venue:"Okänd plan"}]).changes.length,0);
assert.equal(review([row],schedule,[...pitches,{pitch_number:3,name:"Ekäng"}]).changes.length,0);
// The nine team pairs in the reported PDF, compared with cup 45's public schedule.
const existingPairs=[
 [252,"Bromölla","Örebro SK","A"], [253,"Stångebro","Karlstad","C"],
 [254,"Heming","Premium Barcelona","B"], [255,"BK Häcken","Bromölla","A"],
 [256,"Karlstad","Hammarby","C"], [257,"Örebro SK","BK Häcken","A"],
 [258,"AIK","Premium Barcelona","B"], [259,"Hammarby","Stångebro","C"], [260,"Heming","AIK","B"],
];
const reportedPairs=[
 ["Örebro SK","Bromölla"], ["Stångebro","Karlstad"], ["Heming","PremiumBarcelona"],
 ["Bromölla","BK Häcken"], ["Karlstad","Hammarby"], ["Örebro SK","BK Häcken"],
 ["AIK","PremiumBarcelona"], ["Hammarby","Stångebro"], ["Heming","AIK"],
];
const actualCup={...schedule,matches:existingPairs.map(([id,home_label,away_label,group_name])=>({...schedule.matches[0],id,home_label,away_label,group_name}))};
const reportedRows=reportedPairs.map(([home_team,away_team],i)=>({...row,home_team,away_team,group_name:`Grupp ${existingPairs[i][3]}`}));
const recovered=review(reportedRows,actualCup);
assert.equal(recovered.unmatched.length,0);
assert.deepEqual(Array.from(recovered.changes,c=>c.match.id),existingPairs.map(p=>p[0]));
assert.equal(review(reportedRows.map(r=>({...r,time:"09:00",venue:"Sörbyvallen"})),actualCup).unchanged,9);
assert.equal(review([{...reportedRows[2],home_team:"HEMING",away_team:"Premium\u00a0Barcelona"}],actualCup).changes.length,1);
assert.equal(review([{...reportedRows[2],home_team:"Heeming"}],actualCup).changes.length,0,"No fuzzy team-name guesses");
assert.equal(review([{...reportedRows[2],group_name:"Grupp A"}],actualCup).changes.length,0,"A conflicting group must not be ignored");
const similarNames={...actualCup,matches:[...actualCup.matches,{...actualCup.matches[2],id:999,away_label:"PremiumBar celona"}]};
assert.equal(review([reportedRows[2]],similarNames).changes.length,0,"Compact spellings must be unique across the cup");
assert.equal(review([{...row,away_team:"AIK1"}]).changes.length,0);
const repeatPair={...schedule,matches:[{...schedule.matches[0],group_name:"A"},{...schedule.matches[0],id:8,home_label:"AIK",away_label:"Örebro SK",group_name:"B"}]};
assert.equal(review([row],repeatPair).changes.length,0);
assert.equal(review([{...row,group_name:"Grupp B"}],repeatPair).changes[0].match.id,8);
for(const flag of ["played","schedule_locked"]){
 const preserved=review([row],{...schedule,matches:[{...schedule.matches[0],[flag]:true}]});
 assert.equal(preserved.changes.length,0);
 assert.equal(preserved.preserved.length,1);
}
assert.equal(reviewScheduleRevision({matches:[row],unread_rows:["En rad kunde inte läsas"]},schedule,pitches).unmatched.length,1);
const {revisionCommitRows,revisionIsSaved}=load("lib/schedule-revision-commit.ts");
const selectedChanges=recovered.changes;
const committedRows=revisionCommitRows(selectedChanges);
assert.equal(committedRows.length,9);
assert.equal(committedRows[0].expected_scheduled_start,"2026-10-24T09:00:00");
const savedSchedule={...actualCup,matches:selectedChanges.map(row=>({...row.match,scheduled_start:row.nextStart,pitch_number:row.nextPitch}))};
assert.equal(revisionIsSaved(selectedChanges,savedSchedule),true);
assert.equal(revisionIsSaved(selectedChanges,actualCup),false,"A successful HTTP response alone is not proof that the new schedule was saved");
assert.equal(revisionIsSaved(selectedChanges,{...savedSchedule,matches:savedSchedule.matches.slice(1)}),false);
assert.equal(revisionIsSaved(selectedChanges,{...savedSchedule,matches:savedSchedule.matches.map((m,i)=>i?m:{...m,pitch_number:1})}),false);
assert.equal(revisionIsSaved(selectedChanges,null),false);
const {documentFilesError}=load("components/document-dropzone.tsx");
assert.equal(documentFilesError([{name:"schema.pdf",size:1024}]),"");
assert.match(documentFilesError([{name:"schema.exe",size:1024}]),/Välj PDF/);
assert.match(documentFilesError([{name:"schema.pdf",size:0}]),/tom/);
assert.match(documentFilesError([{name:"schema.pdf",size:26*1024*1024}]),/25 MB/);
assert.match(documentFilesError(Array.from({length:13},()=>({name:"schema.pdf",size:1}))),/12 filer/);
console.log("PDF cup update: matching, duplicate rows, dates, protected matches and upload validation PASS");
