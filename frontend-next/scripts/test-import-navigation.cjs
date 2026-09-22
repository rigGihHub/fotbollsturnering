const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

const source = fs.readFileSync(path.join(__dirname, "../src/lib/open-playoff-review.ts"), "utf8");
const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;
const stored = new Map();
const events = [];
const context = {
  exports: {},
  sessionStorage: { setItem: (key, value) => stored.set(key, value) },
  window: { location: { hash: "playoffs" }, dispatchEvent: event => events.push(event) },
  CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options.detail; } },
};
vm.runInNewContext(code, context);
const { includesPlayoffStep, openPlayoffReview, PLAYOFF_REVIEW_REQUEST_KEY, OPEN_PLAYOFF_REVIEW_EVENT } = context.exports;

// A direct review link must remain reachable before the cup type is configured.
for (const type of ["tournament", "matchcamp", "tournament_playoffs", "custom"]) {
  assert.equal(includesPlayoffStep(type, "playoffs"), true);
}
assert.equal(includesPlayoffStep("tournament", "overview"), false);
assert.equal(includesPlayoffStep("matchcamp", "overview"), false);
assert.equal(includesPlayoffStep("tournament_playoffs", "overview"), true);

// Repeat clicks must request a new opening even when the URL hash is unchanged.
openPlayoffReview(17);
openPlayoffReview(17);
assert.equal(events.length, 2);
assert.equal(events[1].type, OPEN_PLAYOFF_REVIEW_EVENT);
assert.equal(events[1].detail, 17);
assert.equal(stored.get(PLAYOFF_REVIEW_REQUEST_KEY), "17");
assert.equal(context.window.location.hash, "playoffs");
openPlayoffReview(23);
assert.equal(stored.get(PLAYOFF_REVIEW_REQUEST_KEY), "23");
console.log("Import navigation: PASS");

const ruleSource = fs.readFileSync(path.join(__dirname, "../src/lib/playoff-import-rules.ts"), "utf8");
const ruleContext = { exports: {} };
vm.runInNewContext(ts.transpileModule(ruleSource, {compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,ruleContext);
const { playoffImportRules } = ruleContext.exports;
const formatted = playoffImportRules({halves:2,minutes_per_half:20,halftime_minutes:null,pitch_break_minutes:0,tie_rule:"Alla matcher får sluta oavgjort.",internal_field:"hidden"});
assert.equal(formatted[0].label,"Matchtid");
assert.equal(formatted[0].value,"2 × 20 min");
assert.equal(formatted[1].value,"0 min");
assert.equal(formatted[2].label,"Vid oavgjort");
assert.equal(formatted.length,3);
assert.equal(playoffImportRules({halves:null,minutes_per_half:null}).length,0);
assert.equal(playoffImportRules({halves:"<bad>",minutes_per_half:-5}).length,0);
console.log("Import rule presentation: PASS");
