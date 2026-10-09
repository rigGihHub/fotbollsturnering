const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const ts=require('typescript');
const React=require('react');
const compile=file=>ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src',file),'utf8'),{compilerOptions:{target:ts.ScriptTarget.ES2020,module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}}).outputText;
const active=code=>({active:true,code,valid_hours:48,expires_at:new Date(Date.now()+86400000).toISOString()});
function nodes(node,out=[]){
 if(!node||typeof node!=='object')return out;
 if(Array.isArray(node)){node.forEach(value=>nodes(value,out));return out;}
 out.push(node);nodes(node.props?.children,out);return out;
}
function text(node){
 if(node==null||typeof node==='boolean')return '';
 if(Array.isArray(node))return node.map(text).join('');
 return typeof node==='object'?text(node.props?.children):String(node);
}
function harness({cupId=1,token='token-one',file='components/role-code-admin.tsx',extraImports={},storage={},ignoreAbortRequests=false}={}){
 let props={cupId,token},slots=[],index=0,dirty=true,tree,effects=[],disposed=false,lateUpdates=0,ignoreAbort=ignoreAbortRequests;
 let timers=new Map(),intervals=new Map(),nextTimer=0,requests=[],copies=[],listeners=new Map();
 const same=(a,b)=>a&&b&&a.length===b.length&&a.every((v,i)=>Object.is(v,b[i]));
 const hooks={...React,
  useState:init=>{const i=index++;if(!slots[i])slots[i]={value:typeof init==='function'?init():init};return [slots[i].value,value=>{if(disposed){lateUpdates++;return;}const next=typeof value==='function'?value(slots[i].value):value;if(!Object.is(next,slots[i].value)){slots[i].value=next;dirty=true;}}];},
  useRef:value=>{const i=index++;return slots[i]??={current:value};},
  useCallback:(fn,deps)=>{const i=index++;if(!same(slots[i]?.deps,deps))slots[i]={deps,value:fn};return slots[i].value;},
  useEffect:(fn,deps)=>{const i=index++;if(!same(slots[i]?.deps,deps)){const previous=slots[i];slots[i]={deps};effects.push(()=>{previous?.cleanup?.();slots[i].cleanup=fn();});}},
 };
 const fetch=(url,options)=>new Promise((resolve,reject)=>{
  const request={url,options,method:options.method||'GET',settled:false,
   success:payload=>{request.settled=true;resolve({ok:true,status:200,json:async()=>payload});},
   http:status=>{request.settled=true;resolve({ok:false,status,json:async()=>({detail:'Internal Server Error'})});},
   fail:error=>{request.settled=true;reject(error||new TypeError('Failed to fetch'));},
  };
  const shouldIgnore=ignoreAbort;
  options.signal?.addEventListener('abort',()=>{if(!shouldIgnore&&!request.settled)request.fail(new DOMException('Aborted','AbortError'));},{once:true});
  requests.push(request);
 });
 const storageRef={getItem:key=>storage[key]??null};
 const windowRef={
  setTimeout:(fn,delay)=>{timers.set(++nextTimer,{fn,delay});return nextTimer;},clearTimeout:id=>timers.delete(id),
  setInterval:(fn,delay)=>{intervals.set(++nextTimer,{fn,delay});return nextTimer;},clearInterval:id=>intervals.delete(id),
  confirm:()=>true,location:{search:'?cup=1',hash:'#reporting'},
  addEventListener:(event,fn)=>listeners.set(event,fn),removeEventListener:event=>listeners.delete(event),
 };
 const moduleRef={exports:{}};
 vm.runInNewContext(compile(file),{
  module:moduleRef,exports:moduleRef.exports,Headers,AbortController,DOMException,URLSearchParams,Date,fetch,window:windowRef,
  navigator:{clipboard:{writeText:async value=>{copies.push(value);}}},localStorage:storageRef,sessionStorage:storageRef,
  require:name=>{
   if(name==='react')return hooks;
   if(name==='react/jsx-runtime')return require(name);
   if(name==='../lib/client-api')return {CLIENT_API_BASE:'https://api.example.test'};
   if(name==='../lib/public-site-url')return {publicSiteUrl:url=>'https://www.cup-navi.com'+url};
   if(name in extraImports)return extraImports[name];
   throw Error(`Unexpected import ${name}`);
  },
 });
 const render=()=>{let guard=0;while(dirty&&!disposed){assert.ok(++guard<25,'render settles');dirty=false;index=0;tree=moduleRef.exports.default(props);const pending=effects;effects=[];pending.forEach(fn=>fn());}return tree;};
 const flush=async()=>{await new Promise(setImmediate);render();};
 const button=label=>nodes(tree).find(node=>node.type==='button'&&text(node)===label);
 const click=label=>{const node=button(label);assert.ok(node,`button ${label} exists`);assert.ok(!node.props.disabled,`button ${label} enabled`);node.props.onClick();render();};
 const unmount=()=>{disposed=true;slots.forEach(slot=>slot.cleanup?.());};
 render();
 return {render,flush,button,click,requests,copies,window:windowRef,text:()=>text(tree),nodes:()=>nodes(tree),unmount,
  changeProps:next=>{props={...props,...next};dirty=true;render();},ignoreAbort:()=>{ignoreAbort=true;},lateUpdates:()=>lateUpdates,
  timeout:()=>{const timer=[...timers].find(([,value])=>value.delay===20000);assert.ok(timer,'request timeout exists');timers.delete(timer[0]);timer[1].fn();},
  event:type=>{listeners.get(type)?.();render();},
 };
}
(async()=>{
 const initial=harness();
 assert.equal(initial.requests.length,1);assert.equal(initial.requests[0].method,'GET');
 assert.equal(initial.requests[0].options.headers.get('Authorization'),'Bearer token-one');
 assert.equal(initial.requests[0].options.cache,'no-store');
 initial.requests[0].http(500);await initial.flush();
 assert.match(initial.text(),/KODSTATUS OKÄND/);assert.doesNotMatch(initial.text(),/INGEN KOD|Failed to fetch|Internal Server Error/);
 assert.ok(initial.button('Generera 4-siffrig kod').props.disabled);
 initial.click('Hämta kodstatus igen');
 initial.requests[1].success(active('1234'));await initial.flush();
 assert.match(initial.text(),/KOD AKTIV/);assert.match(initial.text(),/1234/);
 initial.click('Kopiera kod');await initial.flush();assert.deepEqual(initial.copies,['1234']);
 assert.equal(initial.requests.filter(request=>request.method!=='GET').length,0,'status retry/copy never generates a code');

 // Simulate a write saved by the server, but whose response never reaches the
 // browser. An explicit read must reconcile it rather than repeat the POST.
 initial.nodes().find(node=>node.type==='select').props.onChange({target:{value:'72'}});initial.render();
 const rotate=initial.button('Byt kod');rotate.props.onClick();rotate.props.onClick();initial.render();
 assert.equal(initial.requests.length,3,'synchronous double click creates exactly one mutation');
 assert.equal(initial.requests[2].method,'POST');assert.match(initial.requests[2].url,/\/rotate$/);
 assert.equal(JSON.parse(initial.requests[2].options.body).valid_hours,72);
 initial.requests[2].fail();await initial.flush();
 assert.match(initial.text(),/ÄNDRING EJ BEKRÄFTAD/);assert.match(initial.text(),/Den kan ha genomförts/);
 assert.match(initial.text(),/SENAST HÄMTADE RAPPORTÖRSKOD.*1234/);
 assert.ok(initial.button('Byt kod').props.disabled);assert.ok(initial.button('Kopiera kod').props.disabled);
 initial.button('Byt kod').props.onClick();initial.render();assert.equal(initial.requests.length,3,'guard rejects another mutation while outcome is unknown');
 initial.click('Hämta kodstatus igen');
 initial.requests[3].fail();await initial.flush();
 assert.match(initial.text(),/1234/);assert.match(initial.text(),/fortfarande obekräftad/);
 assert.ok(initial.button('Byt kod').props.disabled);assert.equal(initial.requests.length,4,'failed read does not repeat mutation');
 initial.click('Hämta kodstatus igen');
 initial.requests[4].success(active('5678'));await initial.flush();
 assert.doesNotMatch(initial.text(),/1234|EJ BEKRÄFTAD/);assert.match(initial.text(),/5678/);
 assert.ok(!initial.button('Byt kod').props.disabled);
 assert.equal(initial.nodes().find(node=>node.type==='select').props.value,72,'reconciliation preserves chosen code lifetime');
 assert.equal(initial.requests.filter(request=>request.method==='POST').length,1);
 initial.unmount();

 for(const [label,method,suffix] of [['Förläng 24 timmar','POST','/extend'],['Ta bort kod','DELETE','/reporter']]){
  const control=harness();control.requests[0].success(active('2468'));await control.flush();
  control.click(label);assert.equal(control.requests[1].method,method);assert.ok(control.requests[1].url.endsWith(suffix));
  control.requests[1].http(500);await control.flush();
  assert.ok(control.button(label).props.disabled);assert.match(control.text(),/2468/);
  control.click('Hämta kodstatus igen');assert.equal(control.requests[2].method,'GET');
  control.requests[2].success({active:false,code:null});await control.flush();
  assert.doesNotMatch(control.text(),/2468/);assert.ok(!control.button('Generera 4-siffrig kod').props.disabled);
  assert.equal(control.requests.filter(request=>request.method===method&&method!=='GET').length,1);
  control.unmount();
 }

 const timeout=harness();timeout.timeout();await timeout.flush();
 assert.match(timeout.text(),/Kodstatus kunde inte hämtas/);assert.ok(timeout.button('Hämta kodstatus igen'));
 assert.doesNotMatch(timeout.text(),/Aborted|AbortError/);timeout.unmount();
 const auth=harness();auth.requests[0].http(401);await auth.flush();
 assert.match(auth.text(),/adminsession har gått ut/);assert.ok(auth.button('Generera 4-siffrig kod').props.disabled);auth.unmount();

 // Ignore abort in the mock transport to ensure request identity, not merely
 // AbortController, prevents late responses from overwriting another cup.
 const switched=harness();switched.ignoreAbort();
 switched.requests[0].success(active('1111'));await switched.flush();
 switched.click('Byt kod');const oldWrite=switched.requests[1];
 switched.changeProps({cupId:2,token:'token-two'});
 assert.ok(oldWrite.options.signal.aborted);assert.doesNotMatch(switched.text(),/1111/);
 const newRead=switched.requests[2];assert.match(newRead.url,/cups\/2\//);assert.equal(newRead.options.headers.get('Authorization'),'Bearer token-two');
 newRead.success(active('2222'));await switched.flush();
 oldWrite.success(active('9999'));await switched.flush();
 assert.match(switched.text(),/2222/);assert.doesNotMatch(switched.text(),/9999|1111/);switched.unmount();
 const oldRead=harness({ignoreAbortRequests:true});const pendingRead=oldRead.requests[0];
 oldRead.changeProps({cupId:2});assert.ok(pendingRead.options.signal.aborted);
 oldRead.requests[1].success(active('2222'));await oldRead.flush();
 pendingRead.success(active('1111'));await oldRead.flush();
 assert.match(oldRead.text(),/2222/);assert.doesNotMatch(oldRead.text(),/1111/);oldRead.unmount();
 const unmounted=harness({ignoreAbortRequests:true});unmounted.unmount();
 unmounted.requests[0].success(active('3333'));await unmounted.flush();
 assert.equal(unmounted.lateUpdates(),0,'cleanup prevents state writes after unmount');

 const storage={cupnavi_admin_session_v629:'token',cupnavi_admin_verified_v1:JSON.stringify({token:'token',cups:[{id:1,name:'A'},{id:2,name:'B'}]})};
 const imports=Object.fromEntries(['import-admin','publish-reporting-admin','roster-admin','role-code-admin','team-role-code-admin'].map(name=>['./'+name,{default:name}]));
 const operations=harness({file:'components/admin-operations.tsx',extraImports:imports,storage});
 const role=()=>operations.nodes().find(node=>node.type==='role-code-admin');
 assert.equal(role().key,'1');assert.equal(role().props.cupId,1);
 operations.window.location.search='?cup=2';operations.event('cupnavi:session-refresh');
 assert.equal(role().key,'2');assert.equal(role().props.cupId,2,'parent remounts reporter access when cup changes');operations.unmount();
 console.log('PASS reporter code UI: Swedish unknown/error states, GET-only retry, mutation reconciliation, duplicate-click guard, timeout/auth, abort/stale responses, and cup-key wiring');
})().catch(error=>{console.error(error);process.exitCode=1;});
