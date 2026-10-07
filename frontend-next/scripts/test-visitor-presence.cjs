const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ts=require("typescript");

let clock=0,nextTimer=0,hidden=false,mode="ok";
const timers=new Map(),storage=new Map(),events=new Map(),requests=[],counts=[];
const globals={
  Uint8Array,AbortController,crypto:require("node:crypto").webcrypto,
  localStorage:{getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value)},
  document:{get hidden(){return hidden;},addEventListener:(name,fn)=>events.set(name,fn),removeEventListener:(name,fn)=>{if(events.get(name)===fn)events.delete(name);}},
  window:{addEventListener:(name,fn)=>events.set(name,fn),removeEventListener:(name,fn)=>{if(events.get(name)===fn)events.delete(name);}},
  navigator:{onLine:true},
  setTimeout:(fn,delay)=>{const id=++nextTimer;timers.set(id,{at:clock+delay,fn});return id;},
  clearTimeout:id=>timers.delete(id),
  fetch:async(url,options)=>{requests.push({url,options});if(mode==="fail")throw new Error("Network unavailable");return {ok:true,json:async()=>({active:3})};},
};
function load(file,requireFn=require){
  const module={exports:{}};
  const source=fs.readFileSync(path.join(__dirname,"../src",file),"utf8");
  const code=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2020,module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}}).outputText;
  vm.runInNewContext(code,{module,exports:module.exports,require:requireFn,...globals});
  return module.exports;
}
async function advance(ms){
  const until=clock+ms;
  while(true){
    const entry=[...timers.entries()].filter(([,task])=>task.at<=until).sort((a,b)=>a[1].at-b[1].at)[0];
    if(!entry)break;
    const [id,task]=entry;clock=task.at;timers.delete(id);task.fn();
    await new Promise(setImmediate);
  }
  clock=until;
}
(async()=>{
  const {startVisitorPresence}=load("lib/visitor-presence.ts",name=>name==="./client-api"?{CLIENT_API_BASE:"https://api.example.test"}:require(name));
  let stop=startVisitorPresence("46",count=>counts.push(count));
  assert.equal(requests.length,0,"Presence must not block first render");
  await advance(1000);
  assert.equal(requests.length,1);
  const originalId=JSON.parse(requests[0].options.body).visitor_id;
  assert.match(originalId,/^[a-f0-9]{32}$/);
  assert.equal(requests[0].url,"https://api.example.test/api/public/cups/46/visitors/heartbeat");
  assert.equal(requests[0].options.credentials,"omit");
  assert.equal(requests[0].options.cache,"no-store");
  assert.equal(counts.at(-1),3);
  await advance(30000);
  assert.equal(JSON.parse(requests[1].options.body).visitor_id,originalId);
  hidden=true;events.get("visibilitychange")();
  const before=requests.length;
  await advance(120000);
  assert.equal(requests.length,before,"Hidden pages must not keep a visitor active");
  hidden=false;events.get("visibilitychange")();await advance(0);
  assert.equal(requests.length,before+1);
  stop();const stopped=requests.length;await advance(120000);
  assert.equal(requests.length,stopped);assert.equal(events.size,0);
  stop=startVisitorPresence("slottskampen",count=>counts.push(count));await advance(1000);
  assert.equal(JSON.parse(requests.at(-1).options.body).visitor_id,originalId,"Reloads and tabs reuse the browser identity");
  mode="fail";await advance(30000);
  assert.equal(counts.at(-1),null,"A failed count must not look like a real zero");
  const failedRequests=requests.length;await advance(59999);assert.equal(requests.length,failedRequests);
  await advance(1);assert.equal(requests.length,failedRequests+1,"Failures back off instead of hammering the API");
  stop();
  globals.localStorage.getItem=()=>{throw new Error("Storage blocked");};
  const storageRequests=requests.length;startVisitorPresence("46",()=>{});await advance(1000);
  assert.equal(requests.length,storageRequests,"Blocked identity storage must not invent new visitors per reload");
  let effects=0,starts=0;
  const {VisitorPresence}=load("components/VisitorPresence.tsx",name=>name==="react"?{useState:()=>[null,()=>{}],useEffect:fn=>{effects++;fn();}}:name==="../lib/visitor-presence"?{startVisitorPresence:()=>{starts++;return()=>{};}}:require(name));
  assert.equal(VisitorPresence({publicKey:"46",enabled:false}),null);
  assert.equal(effects,1);assert.equal(starts,0,"Admin previews must not count as public visits");
  console.log("Visitor presence: deferred first request, visible-only heartbeat, browser deduplication, backoff, cleanup and preview exclusion passed.");
})().catch(error=>{console.error(error);process.exitCode=1;});
