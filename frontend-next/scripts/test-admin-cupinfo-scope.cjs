const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

// Run the actual workspace callbacks with controlled requests. This isolates
// cup switching and pending saves from the unrelated team/admin components.
const source = fs.readFileSync(path.join(__dirname, "../src/components/admin-workspace.tsx"), "utf8");
const ast = ts.createSourceFile("admin-workspace.tsx", source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
const pieces = new Map();
function visit(node) {
  if ((ts.isFunctionDeclaration(node) || ts.isClassDeclaration(node)) && node.name && ["saveCupInfo", "cleanCupInfo", "ApiError"].includes(node.name.text)) pieces.set(node.name.text, node.getText(ast));
  if (ts.isVariableDeclaration(node) && ["loadCupInfo", "logout"].includes(node.name.getText(ast))) pieces.set(node.name.getText(ast), `const ${node.getText(ast)};`);
  if (ts.isCallExpression(node) && node.expression.getText(ast) === "useEffect") {
    const callback = node.arguments[0];
    if (callback.getText(ast).includes("cupInfoMounted.current=true")) pieces.set("mountEffect", `const mountEffect=${callback.getText(ast)};`);
    if (callback.getText(ast).includes("writeAdminDraft(`${cupId}:cupinfo`,savedCupinfo,cupinfo)")) pieces.set("draftEffect", `const draftEffect=${callback.getText(ast)};`);
  }
  ts.forEachChild(node, visit);
}
visit(ast);
for (const name of ["saveCupInfo", "cleanCupInfo", "ApiError", "loadCupInfo", "logout", "mountEffect", "draftEffect"]) assert.ok(pieces.has(name), `${name} callback must exist`);
const compiled = ts.transpileModule([...pieces.values()].join("\n") + "\nglobalThis.callbacks={saveCupInfo,loadCupInfo,logout,mountEffect,draftEffect,ApiError};", { compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS } }).outputText;

const cup = (id, extra = {}) => ({ id, name: `Cup ${id}`, admin_revision: 1, show_public_info: true, show_public_offers: true, ...extra });
function harness() {
  const calls = []; const writes = []; const notices = [];
  const context = {
    Error, token: "test", cupId: 45, cupinfo: cup(45), savedCupinfo: cup(45), busy: false,
    cupInfoLoadSequence: { current: 0 }, cupInfoMounted: { current: true },
    cups: [cup(45), cup(46)], error: "", message: "", teams: [{ id: 1 }], groups: [{ id: 2 }],
    scheduleOverview: { match_count: 18 }, rulesOverview: { rules_reviewed: true }, teamFormOpen: true, teamDraft: { name: "Old team" },
    emptyTeam: {}, emptyGroup: {}, TOKEN_KEY: "session", useCallback: fn => fn,
    clearAdminDrafts() {}, localStorage: { removeItem() {} },
    document: { documentElement: { dataset: {} } },
    window: { location: { hash: "#cupinfo" }, dispatchEvent() {} },
    CustomEvent: class { constructor(name, options) { this.name = name; this.detail = options?.detail; } },
    readAdminDraft: (_key, value) => value,
    writeAdminDraft: (...args) => writes.push(args),
    notifyPublicCupUpdate: id => notices.push(id),
    publicWeatherEnabled: () => true,
    publicTabSettings: value => ({ info: value.show_public_info !== false && value.show_public_info !== 0, offers: value.show_public_offers !== false && value.show_public_offers !== 0 }),
  };
  for (const name of ["Cupinfo", "SavedCupinfo", "RulesOverview", "Teams", "Groups", "ScheduleOverview", "EditingTeam", "TeamFormOpen", "TeamDraft", "EditingGroup", "GroupDraft", "Busy", "Error", "Message", "Cups", "Token", "Account", "TrashedCups", "TrashOpen", "CupId", "Password", "RestoringSession"]) {
    const key = name[0].toLowerCase() + name.slice(1);
    context[`set${name}`] = value => { context[key] = typeof value === "function" ? value(context[key]) : value; };
  }
  context.request = (url, options = {}) => {
    let resolve, reject;
    const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
    calls.push({ url, options, resolve, reject }); return promise;
  };
  vm.createContext(context); vm.runInContext(compiled, context);
  const reply = (batch, id, extra = {}) => {
    for (const call of batch) call.resolve(call.url.endsWith("/cupinfo") ? cup(id, extra) : call.url.endsWith("/teams") ? { teams: [] } : call.url.endsWith("/groups") ? { groups: [] } : {});
  };
  return { context, calls, writes, notices, reply, ...context.callbacks };
}

(async () => {
  let h = harness();
  const failedLoad = h.loadCupInfo("test", 46);
  assert.equal(h.context.cupinfo, null, "Changing cup immediately hides the previous cup's form");
  assert.equal(h.context.savedCupinfo, null);
  assert.equal(h.context.teams.length, 0); assert.equal(h.context.groups.length, 0);
  assert.equal(h.context.scheduleOverview, null); assert.equal(h.context.rulesOverview, null);
  assert.equal(h.context.teamFormOpen, false); assert.equal(h.context.teamDraft, h.context.emptyTeam);
  h.calls[0].reject(new Error("Unavailable"));
  await assert.rejects(failedLoad, /Unavailable/);
  assert.equal(h.context.cupinfo, null, "A failed load must not bring old cup information back");

  h = harness();
  const first = h.loadCupInfo("test", 45); const firstBatch = h.calls.slice();
  const second = h.loadCupInfo("test", 46); const secondBatch = h.calls.slice(5);
  h.reply(secondBatch, 46); await second;
  h.reply(firstBatch, 45); await first;
  assert.equal(h.context.cupinfo.id, 46, "An older response must not replace the selected cup");
  const old = h.loadCupInfo("test", 45); const oldBatch = h.calls.slice(10);
  const fresh = h.loadCupInfo("test", 46); h.reply(h.calls.slice(15), 46); await fresh;
  oldBatch[0].reject(new Error("Old failure")); await old;
  assert.equal(h.context.cupinfo.id, 46, "An old error must also be ignored");

  for (const finish of ["unmount", "logout"]) {
    h = harness(); const cleanup = h.mountEffect();
    const pending = h.loadCupInfo("test", 46);
    if (finish === "unmount") cleanup(); else h.logout();
    h.reply(h.calls, 46); await pending;
    assert.equal(h.context.cupinfo, null, `${finish} must ignore pending cup data`);
  }

  h = harness();
  h.context.readAdminDraft = () => cup(99, { name: "Wrong draft" });
  const load = h.loadCupInfo("test", 46); h.reply(h.calls, 46); await load;
  assert.equal(h.context.cupinfo.id, 46, "A malformed draft must not change the cup identity");
  assert.equal(h.context.cupinfo.name, "Cup 46");
  h = harness(); const wrongResponse = h.loadCupInfo("test", 46); h.reply(h.calls, 99);
  await assert.rejects(wrongResponse, /inte den valda cupen/);
  assert.equal(h.context.cupinfo, null);

  h = harness(); h.context.cupId = 46;
  await h.saveCupInfo({ preventDefault() {} }); h.draftEffect();
  assert.equal(h.calls.length, 0, "Stale Cupinfo must never be written to another cup");
  assert.equal(h.writes.length, 0, "Stale drafts must never be filed under the new cup");
  h.context.cupinfo = cup(46); h.context.savedCupinfo = cup(45); h.draftEffect();
  assert.equal(h.writes.length, 0, "Draft baseline must belong to the same cup too");

  h = harness(); h.context.cupinfo = cup(45, { show_public_info: false, show_public_offers: false });
  h.draftEffect(); assert.equal(h.notices.length, 0, "An unsaved checkbox draft must not update public visitors");
  const save = h.saveCupInfo({ preventDefault() {} });
  assert.equal(h.calls[0].options.method, "PUT");
  const body = JSON.parse(h.calls[0].options.body);
  assert.equal(body.show_public_info, false); assert.equal(body.show_public_offers, false);
  h.calls[0].resolve(cup(45, { show_public_info: 0, show_public_offers: 0 })); await save;
  assert.deepEqual(h.notices, [45]);
  assert.match(h.context.message, /Info-fliken är dold och Erbjudanden-fliken är dold/);
  assert.equal(h.context.busy, false);

  h = harness(); const failedSave = h.saveCupInfo({ preventDefault() {} });
  h.calls[0].reject(new Error("Save failed")); await failedSave;
  assert.equal(h.notices.length, 0); assert.match(h.context.error, /Save failed/);
  h = harness(); const pendingSave = h.saveCupInfo({ preventDefault() {} }); h.logout();
  h.calls[0].resolve(cup(45)); await pendingSave;
  assert.equal(h.notices.length, 0, "A pending save result must not restore a logged-out workspace");
  assert.equal(h.context.cupinfo, null);

  h = harness(); const conflict = h.saveCupInfo({ preventDefault() {} });
  h.calls[0].reject(new h.ApiError(409, "Conflict"));
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(h.calls.length, 6);
  h.calls[1].reject(new Error("Reload unavailable")); await conflict;
  assert.match(h.context.error, /senaste versionen kunde inte hämtas/);
  assert.equal(h.context.busy, false); assert.equal(h.notices.length, 0);
  console.log("Admin Cupinfo scope: failed load, response race, logout/unmount, draft identity and confirmed public update passed.");
})().catch(error => { console.error(error); process.exitCode = 1; });
