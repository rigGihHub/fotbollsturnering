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
