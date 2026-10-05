const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");
const React = require("react");

function load(file, requireFn = require, globals = {}) {
  const module = { exports: {} };
  const source = fs.readFileSync(path.join(__dirname, "../src", file), "utf8");
  const code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true } }).outputText;
  vm.runInNewContext(code, { module, exports: module.exports, require: requireFn, URL, ...globals });
  return module.exports;
}

const links = load("lib/public-site-url.ts");
const expected = "https://www.cup-navi.com/cup/slottskampen-6";
for (const host of ["https://cupnavi-web.onrender.com", "https://cup-navi.com", "https://www.cup-navi.com"]) {
  assert.equal(links.publicCupUrl(`${host}/cup/slottskampen-6?preview=1&cup=45&token=synthetic#info`), expected);
}
assert.equal(links.publicSiteUrl("/reporter?cup=slottskampen-6"), "https://www.cup-navi.com/reporter?cup=slottskampen-6");
assert.equal(links.publicSiteUrl("/referee?cup=slottskampen-6&referee=12"), "https://www.cup-navi.com/referee?cup=slottskampen-6&referee=12");
assert.equal(links.publicSiteUrl("/admin"), "https://www.cup-navi.com/admin");

async function checkShare(nativeShare) {
  let copied; let shared;
  const navigator = { clipboard: { writeText: async value => { copied = value; } } };
  if (nativeShare) navigator.share = async value => { shared = value; };
  const { HeaderShareAction } = load("components/HeaderShareAction.tsx", name => {
    if (name === "react") return { ...React, useState: value => [value, () => {}] };
    if (name === "next/navigation") return { usePathname: () => "/cup/slottskampen-6" };
    if (name === "../lib/public-site-url") return links;
    return require(name);
  }, { navigator, document: { title: "Slottskampen" }, window: { location: { origin: "https://cupnavi-web.onrender.com" } } });
  HeaderShareAction().props.onClick();
  await new Promise(setImmediate);
  assert.equal(nativeShare ? shared.url : copied, expected);
}

// Exercise the QR card's real page-URL effect while visiting a Render preview.
let pageUrl; let stateIndex = 0; const effects = []; let currentPath="/cup/slottskampen-6";
const { WeatherShareCard } = load("components/WeatherShareCard.tsx", name => {
  if (name === "react") return { ...React, useState: value => { const index = stateIndex++; return [value, next => { if (index === 2) pageUrl = next; }]; }, useEffect: callback => effects.push(callback) };
  if (name === "next/navigation") return { usePathname: () => currentPath };
  if (name === "../lib/public-site-url") return links;
  if (name === "qrcode") return { toDataURL() { throw new Error("No QR requested before the page URL is set"); } };
  return require(name);
}, { window: { location: { href: "https://cupnavi-web.onrender.com/cup/slottskampen-6?preview=1&cup=45#info" } } });
WeatherShareCard({ cupName: "Slottskampen" });
effects[0]();
assert.equal(pageUrl, expected);
currentPath="/cup/another-cup"; stateIndex=0; effects.length=0;
WeatherShareCard({ cupName: "Another cup" }); effects[0]();
assert.equal(pageUrl,"https://www.cup-navi.com/cup/another-cup");

(async () => {
  await checkShare(false);
  await checkShare(true);
  console.log("Public links: custom domain, reporter/referee parameters, native sharing, clipboard and clean preview QR passed.");
})().catch(error => { console.error(error); process.exitCode = 1; });
