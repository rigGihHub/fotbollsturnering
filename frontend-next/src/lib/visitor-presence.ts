import { CLIENT_API_BASE } from "./client-api";

const VISITOR_KEY="cupnavi:visitor:v1";
const HEARTBEAT_MS=30_000;

function visitorId():string|null {
  try {
    const saved=localStorage.getItem(VISITOR_KEY);
    if(saved&&/^[a-zA-Z0-9_-]{32,64}$/.test(saved))return saved;
    const id=Array.from(crypto.getRandomValues(new Uint8Array(16)),byte=>byte.toString(16).padStart(2,"0")).join("");
    localStorage.setItem(VISITOR_KEY,id);
    return id;
  } catch {return null;}
}

// Kept outside cup-data fetching: analytics never gates rendering or live scores.
export function startVisitorPresence(publicKey:string,onCount:(count:number|null)=>void):()=>void {
  const id=visitorId();
  if(!id)return ()=>{};
  let cancelled=false,busy=false,failures=0;
  let timer:ReturnType<typeof setTimeout>|undefined;
  let controller:AbortController|undefined;
  const schedule=(delay:number)=>{clearTimeout(timer);if(!cancelled&&!document.hidden)timer=setTimeout(()=>void heartbeat(),delay);};
  async function heartbeat(){
    if(cancelled||busy||document.hidden)return;
    if(navigator.onLine===false){onCount(null);schedule(HEARTBEAT_MS);return;}
    busy=true;controller=new AbortController();
    const timeout=setTimeout(()=>controller?.abort(),12_000);
    try {
      const response=await fetch(`${CLIENT_API_BASE}/api/public/cups/${encodeURIComponent(publicKey)}/visitors/heartbeat`,{
        method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({visitor_id:id}),
        cache:"no-store",credentials:"omit",signal:controller.signal,
      });
      if(!response.ok)throw new Error("Visitor count unavailable");
      const data=await response.json();
      if(!Number.isInteger(data.active)||data.active<0)throw new Error("Invalid visitor count");
      failures=0;
      if(!cancelled)onCount(data.active);
    } catch {
      failures+=1;
      if(!cancelled)onCount(null);
    } finally {
      clearTimeout(timeout);busy=false;
      schedule(Math.min(120_000,HEARTBEAT_MS*2**Math.min(failures,2)));
    }
  }
  const visible=()=>{
    clearTimeout(timer);
    if(document.hidden){controller?.abort();return;}
    onCount(null);
    schedule(0);
  };
  document.addEventListener("visibilitychange",visible);
  window.addEventListener("online",visible);
  // Let the cup cover and its matches paint before doing any telemetry work.
  schedule(1000);
  return ()=>{cancelled=true;clearTimeout(timer);controller?.abort();document.removeEventListener("visibilitychange",visible);window.removeEventListener("online",visible);};
}
