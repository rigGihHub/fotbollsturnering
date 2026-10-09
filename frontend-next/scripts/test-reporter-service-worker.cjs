const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const handlers=new Map(),cached=new Map(),origin='https://cupnavi.test';
const key=request=>typeof request==='string'?new URL(request,origin).href:request.url;
const cache={addAll:async assets=>{for(const asset of assets)await cache.add(asset)},add:async asset=>{cached.set(key(asset),new Response(asset==='/reporter'?'<script src="/_next/static/reporter.js"></script><link href="/_next/static/reporter.css"/>':'asset'))},match:async request=>cached.get(key(request))?.clone(),put:async(request,response)=>cached.set(key(request),response)};
const caches={open:async()=>cache,match:cache.match,keys:async()=>[],delete:async()=>true};
vm.runInNewContext(fs.readFileSync('public/sw.js','utf8'),{self:{location:{origin},addEventListener:(type,fn)=>handlers.set(type,fn),skipWaiting:async()=>{},clients:{claim:async()=>{}}},clients:{openWindow:async()=>{}},caches,URL,Response,Promise,Set,fetch:async()=>{throw new TypeError('Offline')}});
(async()=>{
 let work;handlers.get('install')({waitUntil:promise=>work=promise});await work;
 assert(cached.has(origin+'/_next/static/reporter.js')&&cached.has(origin+'/_next/static/reporter.css'),'Offline readiness must include reporter scripts and styles');
 let reply;handlers.get('fetch')({request:{url:origin+'/reporter?cup=slottskampen-6',method:'GET',mode:'navigate'},respondWith:promise=>reply=promise});
 assert((await (await reply).text()).includes('reporter.js'),'A cup-specific reporter URL must use the reporter shell offline');
 reply=undefined;handlers.get('fetch')({request:{url:origin+'/_next/static/reporter.js',method:'GET',mode:'no-cors'},respondWith:promise=>reply=promise});assert.equal(await (await reply).text(),'asset');
 reply=undefined;handlers.get('fetch')({request:{url:origin+'/_next/static/missing.js',method:'GET',mode:'no-cors'},respondWith:promise=>reply=promise});await assert.rejects(reply,TypeError);
 reply=undefined;handlers.get('fetch')({request:{url:origin+'/api/reporter/reporting',method:'GET'},respondWith:promise=>reply=promise});assert.equal(reply,undefined,'Live API data must never be served from a stale shell cache');
 handlers.get('message')({data:{type:'CACHE_REPORTER_ASSETS',assets:[origin+'/_next/static/events.js','https://other.test/_next/static/private.js']},waitUntil:promise=>work=promise});await work;
 assert(cached.has(origin+'/_next/static/events.js'));assert(!cached.has('https://other.test/_next/static/private.js'));
 console.log('PASS offline reporter links, installation asset cache, dynamic assets and API isolation');
})().catch(error=>{console.error(error);process.exitCode=1});
