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
assert.equal(review([{...row,home_team:"AIK",away_team:"Örebro SK"}]).changes.length,0);
assert.equal(review([row],{...schedule,matches:[...schedule.matches,{...schedule.matches[0],id:8}]}).changes.length,0);
assert.equal(review([row],{...schedule,end_date:"2026-10-25"}).changes.length,0);
assert.equal(review([{...row,time:"2026-10-25T10:15"}],{...schedule,end_date:"2026-10-25"}).changes.length,1);
assert.equal(review([{...row,time:"2026-02-30T10:15"}],{...schedule,start_date:"2026-01-01",end_date:"2026-12-31"}).changes.length,0);
assert.equal(review([{...row,time:"25:00"}]).changes.length,0);
assert.equal(review([{...row,venue:"Okänd plan"}]).changes.length,0);
assert.equal(review([row],schedule,[...pitches,{pitch_number:3,name:"Ekäng"}]).changes.length,0);
for(const flag of ["played","schedule_locked"]){
 const preserved=review([row],{...schedule,matches:[{...schedule.matches[0],[flag]:true}]});
 assert.equal(preserved.changes.length,0);
 assert.equal(preserved.preserved.length,1);
}
const {documentFilesError}=load("components/document-dropzone.tsx");
assert.equal(documentFilesError([{name:"schema.pdf",size:1024}]),"");
assert.match(documentFilesError([{name:"schema.exe",size:1024}]),/Välj PDF/);
assert.match(documentFilesError([{name:"schema.pdf",size:0}]),/tom/);
assert.match(documentFilesError([{name:"schema.pdf",size:26*1024*1024}]),/25 MB/);
assert.match(documentFilesError(Array.from({length:13},()=>({name:"schema.pdf",size:1}))),/12 filer/);
console.log("PDF cup update: matching, duplicate rows, dates, protected matches and upload validation PASS");
