const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
function load(path, mocks={}, globals={}) {
  const code=ts.transpileModule(fs.readFileSync(path,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText;
  const module={exports:{}};
  vm.runInNewContext(code,{module,exports:module.exports,atob,require:name=>mocks[name]??require(name),...globals});
  return module.exports;
}
const {reporterSessionDeadline}=load('src/lib/reporter-session.ts');
const issued=Date.parse('2026-09-22T12:00:00Z');
const token=(rev,exp)=>Buffer.from(JSON.stringify({rev,exp:exp/1000})).toString('base64url')+'.signature';
assert.equal(reporterSessionDeadline(token('2026-09-22T12:00:00',issued+7*86400000)),issued+3*86400000);
assert.equal(reporterSessionDeadline(token('2026-09-22T14:00:00+02:00',issued+8*3600000)),issued+8*3600000);
assert.equal(reporterSessionDeadline('bad-token'),0);
const Navigation=load('src/components/reporter-navigation.tsx',{'../lib/reporter-offline':{readReporterCache:()=>null}}).default;
const ReporterModule=load('src/components/reporter-client.tsx',{
  '../lib/client-api':{CLIENT_API_BASE:''},
  '../lib/reporter-session':{reporterSessionDeadline},
  '../lib/reporter-offline':{readReporterQueue:()=>[],isResultMutation:()=>false,isStatusMutation:()=>false},
  './reporter-match-events':{default:()=>null},
  './reporter-navigation':Navigation
});
const Reporter=ReporterModule.default;
const {reporterMatchLifecycle}=ReporterModule;
assert.equal(reporterMatchLifecycle({match_status:'not_started',status:'played'}),'not_started','A saved score must stay editable until the reporter explicitly finishes the match');
assert.equal(reporterMatchLifecycle({match_status:'live',status:'played'}),'live');
assert.equal(reporterMatchLifecycle({match_status:'finished',status:'played'}),'finished');
assert.equal(reporterMatchLifecycle({match_status:null,status:'played'}),'finished','Legacy played matches remain locked');
const html=renderToStaticMarkup(React.createElement(Reporter));
assert.equal((html.match(/<input\b/g)||[]).length,1);
assert.ok(html.includes('inputMode="numeric"')&&html.includes('maxLength="4"'));
assert.ok(!html.includes('Cupens länk')&&html.includes('högst 3 dygn'));
assert.ok(html.includes('aria-label="Byt vy"')&&html.includes('href="/admin"'));
const navigation=renderToStaticMarkup(React.createElement(Navigation,{cup:{id:1,public_slug:'cup-a'}}));
assert.ok(navigation.includes('href="/cup/cup-a?from=reporter"')&&navigation.includes('href="/admin"'));
const Admin=load('src/components/role-code-admin.tsx',{'../lib/client-api':{CLIENT_API_BASE:''}}).default;
const admin=renderToStaticMarkup(React.createElement(Admin,{token:'test',cupId:1}));
assert.ok(admin.includes('value="72"')&&!admin.includes('value="168"'));
assert.ok(admin.includes('Kodens giltighet från skapandet'));
assert.ok(admin.includes('href="/reporter?cup=1"'));
const storage=new Map();
const localStorage={getItem:key=>storage.get(key)??null,setItem:(key,value)=>storage.set(key,value)};
const window={dispatchEvent:()=>{}};
const Offline=load('src/lib/reporter-offline.ts',{}, {localStorage,window,CustomEvent:class {}});
Offline.writeReporterQueue([
  {id:'waiting',kind:'status',cupId:1,matchId:1,createdAt:1,state:'queued',payload:{status:'live',expected_status:'not_started'}},
  {id:'conflict',kind:'status',cupId:1,matchId:2,createdAt:2,state:'conflict',payload:{status:'live',expected_status:'not_started'}},
  {id:'other-cup',kind:'status',cupId:2,matchId:3,createdAt:3,state:'conflict',payload:{status:'live',expected_status:'not_started'}},
]);
assert.equal(JSON.stringify(Offline.reporterQueueSummary(1)),JSON.stringify({pending:1,conflicts:1}));
Offline.retryReporterConflicts(1);
assert.equal(JSON.stringify(Offline.reporterQueueSummary(1)),JSON.stringify({pending:2,conflicts:0}));
Offline.updateReporterMutation('conflict',{state:'conflict'});
Offline.discardReporterConflicts(1);
assert.equal(JSON.stringify(Offline.reporterQueueSummary(1)),JSON.stringify({pending:1,conflicts:0}));
assert.equal(JSON.stringify(Offline.reporterQueueSummary(2)),JSON.stringify({pending:0,conflicts:1}));
console.log('Reporter login: single code field, deadlines and admin options PASS');
