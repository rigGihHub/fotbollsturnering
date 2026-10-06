const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

function load(file, requireFn = require) {
  const module = { exports: {} };
  const source = fs.readFileSync(path.join(__dirname, "../src", file), "utf8");
  const code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true } }).outputText;
  vm.runInNewContext(code, { module, exports: module.exports, require: requireFn, URL, Error });
  return module.exports;
}
const titles = load("lib/cup-share-title.ts");
const links = load("lib/public-site-url.ts");
class CupNaviApiError extends Error { constructor(status) { super("Public API unavailable"); this.status = status; } }
function route(getCup) {
  return load("app/cup/[publicKey]/page.tsx", name => {
    if (name === "react") return { cache: fn => { const calls = new Map(); return key => { if (!calls.has(key)) calls.set(key, fn(key)); return calls.get(key); }; } };
    if (name === "@/lib/api") return { getCup, CupNaviApiError };
    if (name === "@/lib/cup-share-title") return titles;
    if (name === "@/lib/public-site-url") return links;
    if (name === "@/components/PublicCupView") return { PublicCupView: "PublicCupView" };
    if (name === "@/components/public-cup-preview") return { __esModule: true, default: "PublicCupPreview" };
    if (name === "@/components/public-cup-recovery") return { __esModule: true, default: "PublicCupRecovery" };
    return require(name);
  });
}
const props = query => ({ params: Promise.resolve({ publicKey: "46" }), searchParams: Promise.resolve(query || {}) });
(async () => {
  let calls = 0;
  const published = route(async key => { calls++; assert.equal(key, "46"); return { tournament: { name: "Slottskampen 2026" } }; });
  const metadata = await published.generateMetadata(props({ from: "reporter", token: "synthetic" }));
  const title = "CupNavi - Slottskampen 2026";
  assert.equal(metadata.title, title);
  assert.equal(metadata.openGraph.title, title);
  assert.equal(metadata.twitter.title, title);
  assert.equal(metadata.description, "Följ Slottskampen 2026: spelschema, tabeller och resultat.");
  assert.equal(metadata.alternates.canonical, "https://www.cup-navi.com/cup/46");
  assert.equal(metadata.openGraph.url, metadata.alternates.canonical);
  const page = await published.default(props({ from: "reporter" }));
  assert.equal(page.type, "PublicCupView");
  assert.equal(page.props.reporterReturn, true);
  assert.equal(calls, 1, "Metadata and page share a single public cup fetch");
  const preview = route(async () => { throw new Error("Private previews must not fetch public metadata"); });
  const privateMetadata = await preview.generateMetadata(props({ preview: "1", cup: "46" }));
  assert.equal(privateMetadata.robots.index, false);
  assert.equal(privateMetadata.openGraph, undefined);
  assert.equal((await preview.default(props({ preview: "1", cup: "46" }))).type, "PublicCupPreview");
  for (const error of [new CupNaviApiError(404), new CupNaviApiError(429), new CupNaviApiError(503), new TypeError("Network failed")]) {
    const unavailable = route(async () => { throw error; });
    assert.equal((await unavailable.generateMetadata(props())).title, "CupNavi");
    assert.equal((await unavailable.default(props())).type, "PublicCupRecovery");
  }
  console.log("Cup sharing metadata: title, OpenGraph, Twitter, clean canonical, shared fetch, preview privacy and recovery passed.");
})().catch(error => { console.error(error); process.exitCode = 1; });
