const CACHE="cupnavi-next-v2890";
const SHELL=["/","/reporter","/manifest.webmanifest","/cupnavi-emblem-v2642.png","/cupnavi-maskable-v2832.svg"];
self.addEventListener("install",event=>event.waitUntil(caches.open(CACHE).then(async cache=>{
  await cache.addAll(SHELL);
  // Cache the reporter's own scripts and styles before announcing offline readiness.
  const reporter=await cache.match("/reporter"),html=reporter?await reporter.text():"";
  const assets=[...new Set([...html.matchAll(/(?:src|href)="([^" ]*\/_next\/static\/[^" ]+)"/g)].map(match=>match[1].replaceAll("&amp;","&")))];
  await Promise.all(assets.map(asset=>cache.add(asset)));
}).then(()=>self.skipWaiting())));
self.addEventListener("activate",event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener("fetch",event=>{
  if(event.request.method!=="GET") return;
  const url=new URL(event.request.url);
  if(url.origin===self.location.origin&&url.pathname.startsWith('/_next/static/')){
    // Build-hashed assets never change in place. Reuse the exact version and
    // fetch a new URL after an update; never cache live match/API data this way.
    event.respondWith(caches.open(CACHE).then(async cache=>{
      const hit=await cache.match(event.request);
      if(hit)return hit;
      const response=await fetch(event.request);
      if(response.ok)await cache.put(event.request,response.clone());
      return response;
    }));
    return;
  }
  if(url.pathname.startsWith("/api/")||url.pathname.startsWith("/admin")||url.pathname.startsWith("/cup/")) return;
  event.respondWith(fetch(event.request).then(response=>{
    if(response.ok){const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(event.request,copy));}
    return response;
  }).catch(()=>caches.match(event.request).then(async hit=>{
    if(hit)return hit;
    // Cup hints identify the session, but use the same reporter HTML shell.
    if(url.origin===self.location.origin&&url.pathname==="/reporter")return caches.match("/reporter");
    if(event.request.mode==="navigate")return caches.match("/");
    return Response.error();
  })));
});
self.addEventListener("message",event=>{
  if(event.data?.type!=="CACHE_REPORTER_ASSETS"||!Array.isArray(event.data.assets))return;
  const assets=event.data.assets.filter(asset=>{try{const url=new URL(asset,self.location.origin);return url.origin===self.location.origin&&url.pathname.startsWith("/_next/static/")}catch{return false}}).slice(0,100);
  event.waitUntil(caches.open(CACHE).then(cache=>Promise.allSettled(assets.map(asset=>cache.add(asset)))));
});
self.addEventListener("notificationclick",event=>{event.notification.close();event.waitUntil(clients.openWindow(event.notification.data?.url||"/"));});
