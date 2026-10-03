const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

const source = fs.readFileSync(path.join(__dirname,"../src/lib/public-refresh.ts"),"utf8");
const output = ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText;
const moduleRef = {exports:{}};
vm.runInNewContext(output,{module:moduleRef,exports:moduleRef.exports});
const {nextPublicRefreshDelay,nextPublicRefreshBackoff} = moduleRef.exports;

const now = 1_000_000;
assert.equal(nextPublicRefreshDelay([],0,now),120_000);
assert.equal(nextPublicRefreshDelay([{match_status:"finished"}],0,now),120_000);
assert.equal(nextPublicRefreshDelay([{match_status:"live"}],0,now),20_000);
assert.equal(nextPublicRefreshDelay([{match_status:"halftime"}],0,now),20_000);
assert.equal(nextPublicRefreshDelay([{match_status:"live"}],now+90_000,now),90_000);
assert.equal(nextPublicRefreshDelay([],now+30_000,now,true),30_000);
assert.equal(nextPublicRefreshDelay([],now+95_000,now,true),95_000);
assert.equal(nextPublicRefreshBackoff(0),30_000);
assert.equal(nextPublicRefreshBackoff(30_000),60_000);
assert.equal(nextPublicRefreshBackoff(60_000),120_000);
assert.equal(nextPublicRefreshBackoff(30_000,95_000),95_000);
assert.equal(nextPublicRefreshBackoff(60_000,200_000),120_000);
console.log("Public refresh policy OK");
