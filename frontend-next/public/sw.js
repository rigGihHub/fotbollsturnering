const CACHE="cupnavi-next-v2878";
const SHELL=["/","/reporter","/manifest.webmanifest","/cupnavi-emblem-v2642.png","/cupnavi-maskable-v2832.svg"];
self.addEventListener("install",event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL)).then(()=>self.skipWaiting())));
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
  }).catch(()=>caches.match(event.request).then(hit=>hit||caches.match("/"))));
});
self.addEventListener("notificationclick",event=>{event.notification.close();event.waitUntil(clients.openWindow(event.notification.data?.url||"/"));});
