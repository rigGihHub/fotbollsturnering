const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
function load(path, mocks={}) {
  const code=ts.transpileModule(fs.readFileSync(path,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText;
  const module={exports:{}};
  vm.runInNewContext(code,{module,exports:module.exports,atob,require:name=>mocks[name]??require(name)});
  return module.exports;
}
const {reporterSessionDeadline}=load('src/lib/reporter-session.ts');
const issued=Date.parse('2026-09-22T12:00:00Z');
const token=(rev,exp)=>Buffer.from(JSON.stringify({rev,exp:exp/1000})).toString('base64url')+'.signature';
assert.equal(reporterSessionDeadline(token('2026-09-22T12:00:00',issued+7*86400000)),issued+3*86400000);
assert.equal(reporterSessionDeadline(token('2026-09-22T14:00:00+02:00',issued+8*3600000)),issued+8*3600000);
assert.equal(reporterSessionDeadline('bad-token'),0);
const Reporter=load('src/components/reporter-client.tsx',{
  '../lib/client-api':{CLIENT_API_BASE:''},
  '../lib/reporter-session':{reporterSessionDeadline},
  '../lib/reporter-offline':{readReporterQueue:()=>[],isResultMutation:()=>false,isStatusMutation:()=>false},
  './reporter-match-events':{default:()=>null}
}).default;
const html=renderToStaticMarkup(React.createElement(Reporter));
assert.equal((html.match(/<input\b/g)||[]).length,1);
assert.ok(html.includes('inputMode="numeric"')&&html.includes('maxLength="4"'));
assert.ok(!html.includes('Cupens länk')&&html.includes('högst 3 dygn'));
const Admin=load('src/components/role-code-admin.tsx',{'../lib/client-api':{CLIENT_API_BASE:''}}).default;
const admin=renderToStaticMarkup(React.createElement(Admin,{token:'test',cupId:1}));
assert.ok(admin.includes('value="72"')&&!admin.includes('value="168"'));
assert.ok(admin.includes('Kodens giltighet från skapandet'));
assert.ok(admin.includes('href="/reporter"'));
console.log('Reporter login: single code field, deadlines and admin options PASS');
