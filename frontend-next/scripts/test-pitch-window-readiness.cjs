const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");

function load(file, requireFn = require, globals = {}) {
  const module = { exports: {} };
  const source = fs.readFileSync(path.join(__dirname, "../src", file), "utf8");
  const code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText;
  vm.runInNewContext(code, { module, exports: module.exports, require: requireFn, ...globals });
  return module.exports;
}

const navigation = load("lib/venue-return-navigation.ts");
const readiness = load("lib/pitch-window-readiness.ts");
navigation.requestScheduleReturn(45);
assert.equal(navigation.hasScheduleReturn(46), false);
assert.equal(navigation.hasScheduleReturn(45), true);
assert.equal(navigation.consumeScheduleReturn(45), true);
assert.equal(navigation.consumeScheduleReturn(45), false);
navigation.requestScheduleReturn(45);
assert.equal(navigation.consumeScheduleReturn(46), false);
assert.equal(navigation.hasScheduleReturn(45), false);

const requirement = { pitch_number: 1, play_date: "2026-10-24", first_start: "2026-10-24T08:30:00", last_end: "2026-10-24T16:38:00", match_count: 9 };
assert.equal(readiness.requiredPitchHours(requirement), "08:30–16:38");
assert.equal(readiness.requiredPitchHours({ ...requirement, last_end: "2026-10-25T00:38:00" }), "08:30–2026-10-25 00:38");

let schedule;
let stateIndex;
const css = { notice: "notice", error: "error", pending: "pending", requirement: "requirement" };
const ScheduleAdmin = load("components/schedule-admin.tsx", name => {
  if (name === "react") return { ...React, useState(value) { return React.useState(stateIndex++ === 0 ? schedule : value); } };
  if (name === "../lib/pitch-window-readiness") return readiness;
  if (name === "../lib/venue-return-navigation") return navigation;
  if (name === "../lib/client-api") return { CLIENT_API_BASE: "" };
  if (name === "../lib/pitch-label") return { pitchLabel: (number, names) => names[number] || `Plan ${number}` };
  if (name.endsWith(".module.css")) return { default: css, __esModule: true };
  return require(name);
}).default;
const base = { matches: [], match_count: 18, scheduled_count: 18, unscheduled_count: 0, pitch_count: 1, pitch_names: { 1: "Sörbyvallen" }, schedule_dirty: true, conflict_analysis: { ok: true, conflict_count: 0, conflicts: [], match_duration_minutes: 38, pitch_break_minutes: 5, minimum_team_rest_minutes: 45 } };
function renderSchedule(data) {
  schedule = data; stateIndex = 0;
  return renderToStaticMarkup(React.createElement(ScheduleAdmin, { token: "test", cupId: 45 }));
}
let html = renderSchedule({ ...base, pitch_window_readiness: { ready: false, issues: [{ type: "unconfirmed", pitch_number: 1, message: "Bekräfta Sörbyvallens öppettider. Schemat använder planen 08:30–16:38, inklusive matchlängd.", match_ids: [1] }], requirements: [requirement] } });
assert.match(html, /Bekräfta Sörbyvallens öppettider/);
assert.match(html, /href="#venues"/);
assert.match(html, /08:30–16:38/);
assert.equal((html.match(/08:30–16:38/g) || []).length, 1, "Required times should be presented once");
assert.doesNotMatch(html, /Godkänn schemat|SCHEMAT ÄR GODKÄNT|schedule-ready-card|Sparat men inte godkänt/);
html = renderSchedule({ ...base, pitch_window_readiness: { ready: true, issues: [], requirements: [requirement] } });
assert.match(html, /Godkänn schemat/);
assert.match(html, /schedule-ready-card pending/);
html = renderSchedule({ ...base, schedule_dirty: false, pitch_window_readiness: { ready: true, issues: [], requirements: [requirement] } });
assert.match(html, /SCHEMAT ÄR GODKÄNT/);
assert.match(html, /href="#publish"/);
html = renderSchedule({ ...base, pitch_window_readiness: { ready: false, issues: [{ type: "missing_pitch", message: "Match 1 saknar plan. Ange planen under Schema.", match_ids: [1] }], requirements: [] } });
assert.match(html, /Rätta angivna avsparkar och planer i matchlistan/);
assert.doesNotMatch(html, /href="#venues"|Godkänn schemat/);

let venueData = { rules: { pitch_count: 1, synchronized_pitch_times: false }, dates: ["2026-10-24"], pitches: [{ pitch_number: 1, name: "Sörbyvallen" }], windows: [{ pitch_number: 1, play_date: "2026-10-24", start_time: "08:00", end_time: "17:00", confirmed: false }], scheduled_count: 18, schedule_dirty: true, schedule_requirements: [requirement] };
const VenueAdmin = load("components/venue-admin.tsx", name => {
  if (name === "../lib/use-admin-draft") return { useAdminDraft: () => ({ data: venueData, dirty: false, setData() {}, accept() {} }) };
  if (name === "../lib/admin-draft") return load("lib/admin-draft.ts");
  if (name === "./admin-draft-status") return { default: () => null, __esModule: true };
  if (name === "../lib/pitch-window-readiness") return readiness;
  if (name === "../lib/venue-return-navigation") return navigation;
  if (name === "../lib/client-api") return { CLIENT_API_BASE: "" };
  if (name.endsWith(".module.css")) return { default: css, __esModule: true };
  return require(name);
}).default;
const renderVenue = cupId => renderToStaticMarkup(React.createElement(VenueAdmin, { token: "test", cupId }));
assert.match(renderVenue(45), /Spara och fortsätt till Regler/);
navigation.requestScheduleReturn(45);
html = renderVenue(45);
assert.match(html, /Spara och återgå till Schema/);
assert.match(html, /Schemat använder 08:30–16:38/);
assert.match(html, /inklusive sista matchens sluttid/);
assert.match(renderVenue(46), /Spara och fortsätt till Regler/);

const publication = { tournament: { is_published: false }, ready: false, blockers: ["Plan 1 saknar bekräftad öppettid."], schedule_conflict_analysis: { conflicts: [] } };
let publishState = 0;
const PublishAdmin = load("components/publish-reporting-admin.tsx", name => {
  if (name === "react") return { ...React, useCallback: callback => callback, useEffect() {}, useMemo: callback => callback(), useState: value => [publishState++ === 0 ? publication : value, () => {}] };
  if (name === "../lib/client-api") return { CLIENT_API_BASE: "" };
  if (name === "../lib/venue-return-navigation") return navigation;
  if (name === "./match-events-admin") return { default: () => null, __esModule: true };
  return require(name);
}).default;
function allNodes(node) {
  if (!node || typeof node !== "object") return [];
  return [node, ...[node.props?.children].flat(Infinity).flatMap(allNodes)];
}
const publicTree = PublishAdmin({ token: "test", cupId: 45, mode: "publish" });
const venueLinks = allNodes(publicTree).filter(node => node.type === "a" && node.props.href === "#venues");
assert.equal(venueLinks.length, 2, "Checklist and footer must both offer the relevant step");
for (const link of venueLinks) {
  navigation.consumeScheduleReturn(45);
  link.props.onClick();
  assert.equal(navigation.hasScheduleReturn(45), true);
  assert.equal(navigation.hasScheduleReturn(46), false);
}
assert.equal(allNodes(publicTree).find(node => node.type === "button" && node.props.className === "admin-action-primary").props.disabled, true);

// Exercise the actual saving callback, including failed verification. Navigation
// must follow a verified save, and the return request must survive an error.
async function saveVenue({ cupId = 45, fails = false, verifies = true, draft = venueData, current = venueData, windowFailure = false } = {}) {
  let done;
  const finished = new Promise(resolve => { done = resolve; });
  const browser = { location: { hash: "#venues" }, dispatchEvent() {} };
  const calls = [];
  let edited; let error = ""; let hookIndex = 0;
  const ActualVenue = load("components/venue-admin.tsx", name => {
    if (name === "react") return { ...React, useCallback: callback => callback, useEffect() {}, useState: value => { const index = hookIndex++; return [typeof value === "function" ? value() : value, next => { if(index === 2) error = next; if (next === false) done(); }]; } };
    if (name === "../lib/use-admin-draft") return { useAdminDraft: () => ({ data: draft, dirty: false, setData(next) { edited = next; }, accept() {} }) };
    if (name === "../lib/admin-draft") return load("lib/admin-draft.ts");
    if (name === "./admin-draft-status") return { default: () => null, __esModule: true };
    if (name === "../lib/pitch-window-readiness") return readiness;
    if (name === "../lib/venue-return-navigation") return navigation;
    if (name === "../lib/client-api") return { CLIENT_API_BASE: "" };
    if (name.endsWith(".module.css")) return { default: css, __esModule: true };
    return require(name);
  }, { window: browser, Headers, Event, fetch: async (url, options) => {
    calls.push({ url, options });
    if (fails) throw new Error("Unavailable");
    if (windowFailure && url.includes("/windows/")) return { ok: false, json: async () => ({ detail: "Tidsfönstren överlappar varandra" }) };
    const source = options.method ? draft : current;
    const data = { ...source, windows: source.windows.map(row => ({ ...row, confirmed: verifies })) };
    return { ok: true, json: async () => data };
  } }).default;
  function findSave(node) {
    if (!node || typeof node !== "object") return null;
    if (node.props?.["data-admin-save-next"]) return node;
    return [node.props?.children].flat(Infinity).map(findSave).find(Boolean);
  }
  findSave(ActualVenue({ token: "test", cupId })).props.onClick();
  await finished;
  assert.ok(calls.every(call => !call.url.includes("/schedule")), "Saving venues must not rewrite match times");
  return { hash: browser.location.hash, calls, edited, error };
}
(async () => {
  navigation.consumeScheduleReturn(45);
  assert.equal((await saveVenue()).hash, "rules");
  navigation.requestScheduleReturn(45);
  assert.equal((await saveVenue({ fails: true })).hash, "#venues");
  assert.equal(navigation.hasScheduleReturn(45), true);
  assert.equal((await saveVenue({ verifies: false })).hash, "#venues");
  assert.equal(navigation.hasScheduleReturn(45), true);
  assert.equal((await saveVenue()).hash, "schedule");
  assert.equal(navigation.hasScheduleReturn(45), false);
  navigation.requestScheduleReturn(45);
  assert.equal((await saveVenue({ cupId: 46 })).hash, "rules");
  const oldWindow = { ...venueData.windows[0], play_date: "2026-10-25", start_time: "10:00" };
  const stale = { ...venueData, windows: [...venueData.windows, oldWindow] };
  let attempt = await saveVenue({ draft: stale });
  assert.equal(attempt.hash, "#venues");
  assert.equal(attempt.calls.length, 1);
  assert.ok(attempt.calls.every(call => !call.options.method), "An out-of-date draft must stop before any mutation");
  assert.match(attempt.error, /Sörbyvallen.*2026-10-25/);
  assert.match(attempt.error, /2026-10-24.*Cupinfo/);
  attempt = await saveVenue({ draft: { ...stale, dates: ["2026-10-24", "2026-10-25"] } });
  assert.equal(attempt.hash, "#venues");
  assert.equal(attempt.calls.length, 1);
  assert.deepEqual(Array.from(attempt.edited.dates), ["2026-10-24"]);
  assert.equal(attempt.edited.windows.length, 2, "Both current edits and the out-of-date draft must survive");
  assert.equal(attempt.edited.windows.find(row => row.play_date === "2026-10-25").start_time, "10:00");
  assert.match(attempt.error, /Cupens datum har ändrats.*Cupinfo/);
  // restoreDraft can leave only the old day's rows even though current dates
  // already came from the server. That must not verify an empty save as success.
  attempt = await saveVenue({ draft: { ...venueData, windows: [oldWindow] } });
  assert.equal(attempt.hash, "#venues");
  assert.equal(attempt.calls.length, 1);
  assert.equal(attempt.edited.windows.length, 2);
  assert.equal(attempt.edited.windows.find(row => row.play_date === "2026-10-24").start_time, "08:00");
  assert.match(attempt.error, /Plantider saknades.*Kontrollera dagarna/);
  attempt = await saveVenue({ windowFailure: true });
  assert.match(attempt.error, /Sörbyvallen, 2026-10-24: Tidsfönstren överlappar/);
  assert.equal(attempt.hash, "#venues");
  const original = venueData;
  venueData = stale;
  html = renderVenue(45);
  assert.match(html, /Plantider för andra datum/);
  assert.match(html, /2026-10-25.*10:00/);
  assert.match(html, /Uteslut dessa tider från sparningen/);
  assert.match(html, /href="#cupinfo"/);
  assert.match(html, /data-admin-save-next="true"[^>]*disabled/);
  venueData = { ...original, preserved_window_dates: ["2026-10-25"] };
  html = renderVenue(45);
  assert.match(html, /Plantider för tidigare cupdatum/);
  assert.match(html, /De ingår inte i cupens aktuella dagar/);
  venueData = original;
  // Click the real exclusion and undo handlers across a simulated step remount.
  const archiveRows = new Map();
  const sessionStorage = { getItem: key => archiveRows.get(key) || null, setItem: (key, value) => archiveRows.set(key, value), removeItem: key => archiveRows.delete(key) };
  const drafts = load("lib/admin-draft.ts", require, { sessionStorage });
  let editorData = stale; let hooks = []; let hookCursor = 0;
  const ArchiveVenue = load("components/venue-admin.tsx", name => {
    if (name === "react") return { ...React, useCallback: callback => callback, useEffect() {}, useState: value => { const index = hookCursor++; if (!(index in hooks)) hooks[index] = typeof value === "function" ? value() : value; return [hooks[index], next => { hooks[index] = next; }]; } };
    if (name === "../lib/use-admin-draft") return { useAdminDraft: () => ({ data: editorData, dirty: true, setData: next => { editorData = next; }, accept() {} }) };
    if (name === "../lib/admin-draft") return drafts;
    if (name === "./admin-draft-status") return { default: () => null, __esModule: true };
    if (name === "../lib/pitch-window-readiness") return readiness;
    if (name === "../lib/venue-return-navigation") return navigation;
    if (name === "../lib/client-api") return { CLIENT_API_BASE: "" };
    if (name.endsWith(".module.css")) return { default: css, __esModule: true };
    return require(name);
  }).default;
  function editorTree() { hookCursor = 0; return ArchiveVenue({ token: "test", cupId: 45 }); }
  let tree = editorTree();
  allNodes(tree).find(node => node.type === "button" && node.props.children === "Uteslut dessa tider från sparningen").props.onClick();
  assert.equal(editorData.windows.length, 1);
  assert.equal(drafts.readVenueWindowArchive(45).length, 1);
  assert.equal(drafts.readVenueWindowArchive(46).length, 0);
  editorData = { ...editorData, dates: ["2026-10-24", "2026-10-25"], windows: [...editorData.windows, { ...oldWindow, start_time: "09:00" }] };
  hooks = []; // Remount after Cupinfo makes the excluded date active again.
  tree = editorTree();
  allNodes(tree).find(node => node.type === "button" && node.props.children === "Ångra uteslutning").props.onClick();
  assert.equal(editorData.windows.length, 2);
  assert.equal(editorData.windows.filter(row => row.play_date === "2026-10-25").length, 1, "Undo replaces the same plan/day, avoiding duplicate intervals");
  assert.equal(editorData.windows.find(row => row.play_date === "2026-10-25").start_time, "10:00");
  assert.equal(drafts.readVenueWindowArchive(45).length, 0);
  console.log("Pitch-window readiness: prerequisite UI, required hours, verified save and cup-scoped return passed.");
})().catch(error => { console.error(error); process.exitCode = 1; });
