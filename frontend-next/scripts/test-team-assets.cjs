const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const vm=require("node:vm");
const file=path.join(__dirname,"../src/lib/team-asset-search.ts");
const moduleBox={exports:{}};
vm.runInNewContext(ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022},
}).outputText,{module:moduleBox,exports:moduleBox.exports,Error});
const {searchAndSaveTeamAssets}=moduleBox.exports;
const fixture={
  identity_status:"exact",home_verified:true,away_verified:false,logo_verified:false,
  home_color_1:"#F4C430",home_color_2:"#111827",home_pattern:"Vertikala ränder",
  away_color_1:"#FFFFFF",away_color_2:"#111827",away_pattern:"Helfärgad",
  logo_url:"",logo_source_url:"",
};
const plain=value=>JSON.parse(JSON.stringify(value));
async function run(options={},response=fixture){
  const calls=[],writes=[];
  const result=await searchAndSaveTeamAssets({
    kitMode:"home",showLogos:false,existingLogo:"",
    lookup:async(focus,mode)=>{calls.push({focus,mode});return response},
    save:async patch=>writes.push(plain(patch)),
    ...options,
  });
  return {result:plain(result),calls,writes};
}
(async()=>{
  // Reproduces screenshot: missing crest must not turn a kit lookup into logo.
  let r=await run();
  assert.deepEqual(r.calls,[{focus:"kit",mode:"home"}]);
  assert.deepEqual(r.writes,[{primary_color:"#F4C430",home_color_2:"#111827",home_pattern:"Vertikala ränder"}]);
  assert.equal(r.result.updated,true);assert.deepEqual(r.result.issues,[]);
  // Missing away kit must not discard home colors/pattern.
  r=await run({kitMode:"both"});
  assert.equal(r.writes.length,1);assert.deepEqual(r.result.issues,["Borta: behöver kontrolleras."]);
  r=await run({kitMode:"both"},{...fixture,away_verified:true});
  assert.equal(r.writes[0].away_pattern,"Helfärgad");assert.deepEqual(r.result.issues,[]);
  // Away-only verified partial result and exact identity gate.
  r=await run({kitMode:"both"},{...fixture,home_verified:false,away_verified:true});
  assert.ok(!("primary_color" in r.writes[0]));assert.ok("secondary_color" in r.writes[0]);
  for(const identity_status of ["ambiguous","likely","unknown"]){
    r=await run({}, {...fixture,identity_status});assert.equal(r.writes.length,0);
  }
  r=await run({}, {...fixture,home_verified:false});assert.equal(r.writes.length,0);
  // Logo errors must not discard a saved kit.
  const order=[];
  r=await run({
    showLogos:true,
    lookup:async focus=>{order.push(focus);if(focus==="logo")throw Error("timeout");return fixture},
    save:async patch=>order.push(plain(patch)),
  });
  assert.equal(order[0],"kit");assert.equal(order[1].home_pattern,"Vertikala ränder");assert.equal(order[2],"logo");
  assert.equal(r.result.updated,true);assert.equal(r.result.failed,true);
  // No assets selected, and logos only: never send kit_mode=none to backend.
  r=await run({kitMode:"none"});assert.equal(r.calls.length,0);assert.equal(r.result.skipped,true);
  r=await run({kitMode:"none",showLogos:true},{...fixture,logo_verified:true,logo_url:"https://club.example/logo.png",logo_source_url:"https://club.example"});
  assert.deepEqual(r.calls,[{focus:"logo",mode:"both"}]);
  assert.deepEqual(Object.keys(r.writes[0]).sort(),["logo_source_url","logo_url"]);
  assert.deepEqual(r.result.issues,[]);
  r=await run({showLogos:true,existingLogo:"https://club.example/logo.png"});
  assert.equal(r.calls.length,1);assert.equal(r.calls[0].focus,"kit");
  // Rate limit stops requests, preserving prior saves.
  r=await run({showLogos:true,lookup:async focus=>{if(focus==="logo")throw Error("AI_RATE_LIMIT 429");return fixture}});
  assert.equal(r.result.updated,true);assert.equal(r.result.stop,true);assert.equal(r.writes.length,1);
  // Failed persistence is never counted as an update.
  r=await run({save:async()=>{throw Error("write failed")}});
  assert.equal(r.result.updated,false);assert.equal(r.result.failed,true);
  for(let i=0;i<9;i++){r=await run();assert.equal(r.result.updated,true);}
  console.log("Team asset search: routing, selected modes, colors/patterns, partial saves, identity, errors and nine-team regression PASS");
})().catch(error=>{console.error(error);process.exitCode=1});
