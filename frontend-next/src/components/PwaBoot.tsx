"use client";

import { useEffect } from "react";

export function PwaBoot() {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;

    if (process.env.NODE_ENV !== "production") {
      navigator.serviceWorker.getRegistrations().then((registrations) => {
        registrations.forEach((registration) => registration.unregister().catch(() => false));
      }).catch(() => undefined);
      if ("caches" in window) {
        caches.keys().then((keys) => Promise.all(keys.filter((key) => key.startsWith("cupnavi")).map((key) => caches.delete(key)))).catch(() => undefined);
      }
      return;
    }

    // Installing the offline shell also fetches several pages. Let the actual
    // cup and its controls load first instead of competing for the connection.
    const timer=window.setTimeout(()=>{
      void navigator.serviceWorker.register("/sw.js").then(()=>navigator.serviceWorker.ready).then(registration=>{
        if(window.location.pathname!=="/reporter")return;
        const assets=performance.getEntriesByType("resource").map(entry=>entry.name).filter(name=>{
          const url=new URL(name);return url.origin===window.location.origin&&url.pathname.startsWith("/_next/static/");
        });
        registration.active?.postMessage({type:"CACHE_REPORTER_ASSETS",assets});
      }).catch(()=>undefined);
    },2000);
    return()=>window.clearTimeout(timer);
  }, []);

  return null;
}
