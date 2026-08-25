const CACHE="cupnavi-pwa-v160";
const APP_SHELL=["./","./index.html","./config.js","./app.js","./styles.css","./manifest.webmanifest"];

self.addEventListener("install",event=>{
  event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(APP_SHELL)));
  self.skipWaiting();
});
self.addEventListener("activate",event=>{
  event.waitUntil(
    caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))))
  );
  self.clients.claim();
});

self.addEventListener("message",event=>{
  const data=event.data||{};
  if(data.type!=="CACHE_PUBLIC_URLS" || !Array.isArray(data.urls)) return;

  event.waitUntil((async()=>{
    const cache=await caches.open(CACHE);
    const results=[];
    for(const rawUrl of data.urls){
      try{
        const req=new Request(rawUrl,{method:"GET",credentials:"omit"});
        const resp=await fetch(req);
        if(!resp.ok) throw new Error(`HTTP ${resp.status}`);
        await cache.put(req,resp.clone());
        results.push({url:rawUrl,ok:true});
      }catch(error){
        results.push({url:rawUrl,ok:false,error:String(error)});
      }
    }
    if(event.ports && event.ports[0]){
      event.ports[0].postMessage({
        type:"CACHE_PUBLIC_URLS_DONE",
        ok:results.every(item=>item.ok),
        results,
      });
    }
  })());
});

self.addEventListener("fetch",event=>{
  const req=event.request;
  if(req.method!=="GET") return;
  const url=new URL(req.url);

  if(url.pathname.includes("/api/public/")){
    event.respondWith(
      fetch(req).then(resp=>{
        const clone=resp.clone();
        caches.open(CACHE).then(cache=>cache.put(req,clone));
        return resp;
      }).catch(()=>caches.match(req))
    );
    return;
  }

  // Navigations can contain cup/team query parameters. Those URLs are not
  // literal app-shell cache keys, so always fall back to the cached index.
  if(req.mode==="navigate"){
    event.respondWith(
      fetch(req).catch(async()=>{
        return (await caches.match("./index.html")) ||
               (await caches.match("./")) ||
               Response.error();
      })
    );
    return;
  }

  event.respondWith(caches.match(req).then(hit=>hit||fetch(req)));
});
