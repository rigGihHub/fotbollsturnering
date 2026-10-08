const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const root = path.resolve(__dirname, '../src');

function loadRoute(env, fetch) {
  const cache = new Map();
  function load(file) {
    if (!path.extname(file)) file += '.ts';
    if (cache.has(file)) return cache.get(file);
    const module = {exports: {}};
    vm.runInNewContext(ts.transpileModule(fs.readFileSync(file, 'utf8'), {
      compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020},
    }).outputText, {
      module, exports: module.exports, process: {env}, fetch,
      Response, AbortSignal, TextDecoder,
      require: name => name.startsWith('@/') ? load(path.join(root, name.slice(2))) : require(name),
    });
    cache.set(file, module.exports);
    return module.exports;
  }
  return load(path.join(root, 'app/cup/[publicKey]/pdf/route.ts')).GET;
}

(async () => {
  const requests = [];
  const pdf = '%PDF-1.4\nfixture\n%%EOF';
  const get = loadRoute({NODE_ENV: 'production'}, async (url, options) => {
    requests.push({url, options});
    return new Response(pdf, {headers: {
      'Content-Type': 'application/pdf',
      'Content-Disposition': "attachment; filename*=UTF-8''slottskampen.pdf",
    }});
  });
  const result = await get(new Request('https://www.cup-navi.com/cup/46/pdf'), {params: Promise.resolve({publicKey: '46'})});
  assert.equal(requests[0].url, 'https://cupnavi-api.onrender.com/api/public/cups/46/pdf');
  assert.equal(requests[0].options.cache, 'no-store');
  assert.equal(result.status, 200);
  assert.equal(await result.text(), pdf);
  assert.equal(result.headers.get('content-disposition'), "attachment; filename*=UTF-8''slottskampen.pdf");

  const missing = loadRoute({NODE_ENV: 'production', CUPNAVI_API_BASE: 'https://api.example.test/'}, async url => {
    assert.equal(url, 'https://api.example.test/api/public/cups/cup%20name/pdf');
    return new Response('{"detail":"Not Found"}', {status: 404});
  });
  const failure = await missing(new Request('https://www.cup-navi.com/cup/test/pdf'), {params: Promise.resolve({publicKey: 'cup name'})});
  assert.equal(failure.status, 404);
  assert(!/inte publicerad/i.test(await failure.text()), 'A generic PDF failure must not claim publication status');

  const invalid = loadRoute({NODE_ENV: 'production'}, async () => new Response('invalid document', {headers: {'Content-Type': 'application/pdf'}}));
  assert.equal((await invalid(new Request('https://www.cup-navi.com/cup/46/pdf'), {params: Promise.resolve({publicKey: '46'})})).status, 502);
  console.log('PASS public PDF production routing, exact key, download headers, error wording and file validation');
})().catch(error => {console.error(error); process.exitCode = 1;});
