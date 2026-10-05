const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");
const React = require("react");
const {renderToStaticMarkup} = require("react-dom/server");

function load(file, extra = {}) {
  const source = fs.readFileSync(path.join(__dirname, "../src", file), "utf8");
  const output = ts.transpileModule(source, {compilerOptions: {target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX}}).outputText;
  const moduleRef = {exports: {}};
  vm.runInNewContext(output, {module: moduleRef, exports: moduleRef.exports, require, ...extra});
  return moduleRef.exports;
}

async function main() {
  let attempts = 0;
  const timeouts = [];
  const urls = [];
  let response = () => ({ok: true, json: async () => ({sponsors: [], offers: []})});
  const api = load("lib/api.ts", {
    window: {},
    require: name => name === "./client-api" ? {CLIENT_API_BASE: "https://api.example"} : require(name),
    AbortSignal: {timeout: ms => {timeouts.push(ms); return {}; }},
    setTimeout: callback => callback(),
    fetch: async url => {attempts++; urls.push(url); return response();},
  });
  await api.getPartners("cup / one");
  assert.equal(timeouts[0], 20000);
  assert.equal(urls[0], "https://api.example/api/public/cups/cup%20%2F%20one/partners");
  attempts = 0;
  response = () => {throw new Error("Timed out");};
  await assert.rejects(api.getPartners("cup-one"), /Timed out/);
  assert.equal(attempts, 2, "Partner failures must not retry four times");
  attempts = 0;
  response = () => ({ok: false, status: 404, headers: {get: () => null}});
  await assert.rejects(api.getPartners("cup-one"), error => error.status === 404);
  assert.equal(attempts, 1);
  response = () => ({ok: true, json: async () => ({})});
  await api.getStatistics("cup-one");
  assert.equal(timeouts.at(-1), 6500, "Other API requests retain their timeout");

  const {PublicSponsors} = load("components/PublicSponsors.tsx");
  const partners = {sponsors: [{id: 1, name: "Lokala Banken", description: "Stöttar cupen", website_url: "https://banken.example"}], offers: []};
  const render = props => renderToStaticMarkup(React.createElement(PublicSponsors, {partners: null, loading: false, error: false, onRetry() {}, ...props}));
  assert.match(render({loading: true}), /Hämtar sponsorer/);
  assert.match(render({error: true}), /Försök igen/);
  assert.match(render({partners: {sponsors: [], offers: []}}), /Inga sponsorer publicerade/);
  const cached = render({partners, error: true});
  assert.match(cached, /Lokala Banken/);
  assert.match(cached, /Visar senast hämtade uppgifter/);
  assert.match(cached, /href="https:\/\/banken.example"/);
  assert.match(cached, /rel="noopener noreferrer"/);
  console.log("Public partners timeout, retry and Info rendering OK");
}
main().catch(error => {console.error(error); process.exitCode = 1;});
