"use client";

import {useCallback,useEffect,useRef,useState} from "react";
import {CLIENT_API_BASE} from "../lib/client-api";
import {publicSiteUrl} from "../lib/public-site-url";

type Status={active:boolean;created_at?:string|null;rotated_at?:string|null;expires_at?:string|null;valid_hours?:number;code?:string|null};
type Snapshot={cupId:number;token:string;status:Status};
type Action="rotate"|"extend"|"remove";

class CodeRequestError extends Error {
 constructor(public readonly status:number){super(`Kodstatus ${status}`);}
}

async function req(path:string,token:string,controller:AbortController,init:RequestInit={}):Promise<Status>{
 const headers=new Headers(init.headers);
 headers.set("Authorization",`Bearer ${token}`);
 if(init.body)headers.set("Content-Type","application/json");
 const timer=window.setTimeout(()=>controller.abort(),20_000);
 try{
  const response=await fetch(`${CLIENT_API_BASE}${path}`,{...init,headers,signal:controller.signal,cache:"no-store"});
  if(!response.ok)throw new CodeRequestError(response.status);
  const payload=await response.json();
  if(!payload||typeof payload.active!=="boolean")throw new Error("Kodstatus saknas");
  return payload as Status;
 }finally{window.clearTimeout(timer);}
}

function readError(error:unknown):string{
 if(error instanceof CodeRequestError&&error.status===401)return "Din adminsession har gått ut. Logga in igen och hämta kodstatus.";
 if(error instanceof CodeRequestError&&(error.status===403||error.status===404))return "Kodstatus kunde inte hämtas. Kontrollera att du har behörighet till den valda cupen och försök igen.";
 return "Kodstatus kunde inte hämtas just nu. Försök igen om en stund. Hämtningen ändrar inga koder.";
}

export default function RoleCodeAdmin({token,cupId,publicSlug}:{token:string;cupId:number;publicSlug?:string|null}){
 const [snapshot,setSnapshot]=useState<Snapshot|null>(null);
 const data=snapshot?.cupId===cupId&&snapshot.token===token?snapshot.status:null;
 const [validHours,setValidHours]=useState(48);
 const [loading,setLoading]=useState(true);
 const [busy,setBusy]=useState(false);
 const [statusIssue,setStatusIssue]=useState(false);
 const [writeUncertain,setWriteUncertain]=useState(false);
 const [error,setError]=useState("");
 const [copied,setCopied]=useState<"code"|"link"|null>(null);
 const [now,setNow]=useState(()=>Date.now());
 const requestRef=useRef<AbortController|null>(null);
 const statusIssueRef=useRef(false);
 const writeUncertainRef=useRef(false);
 const hoursInitializedRef=useRef(false);
 const copyIdRef=useRef(0);
 const copyTimerRef=useRef<number|null>(null);

 const load=useCallback(async()=>{
  if(requestRef.current)return;
  const controller=new AbortController();
  requestRef.current=controller;
  setLoading(true);setError("");setCopied(null);
  try{
   const status=await req(`/api/admin/cups/${cupId}/role-codes/reporter`,token,controller);
   if(requestRef.current!==controller)return;
   setSnapshot({cupId,token,status});
   if(!hoursInitializedRef.current){setValidHours(status.valid_hours||48);hoursInitializedRef.current=true;}
   statusIssueRef.current=false;writeUncertainRef.current=false;
   setStatusIssue(false);setWriteUncertain(false);
  }catch(reason){
   if(requestRef.current!==controller)return;
   statusIssueRef.current=true;setStatusIssue(true);
   setError(readError(reason)+(writeUncertainRef.current?" Den senaste ändringen är fortfarande obekräftad. Ingen ny kod skapas av återförsöket.":""));
  }finally{
   if(requestRef.current===controller){requestRef.current=null;setLoading(false);}
  }
 },[cupId,token]);

 useEffect(()=>{
  setSnapshot(null);setValidHours(48);setBusy(false);setError("");setCopied(null);
  statusIssueRef.current=false;writeUncertainRef.current=false;hoursInitializedRef.current=false;
  setStatusIssue(false);setWriteUncertain(false);
  void load();
  return()=>{
   const request=requestRef.current;requestRef.current=null;request?.abort();
   copyIdRef.current+=1;
   if(copyTimerRef.current!==null)window.clearTimeout(copyTimerRef.current);
  };
 },[load]);
 useEffect(()=>{const timer=window.setInterval(()=>setNow(Date.now()),1000);return()=>window.clearInterval(timer);},[]);

 const expiry=data?.expires_at?new Date(data.expires_at).getTime():NaN;
 const active=Boolean(data?.active&&(!Number.isFinite(expiry)||expiry>now));
 const newCode=data?.code||"";
 const remaining=Number.isFinite(expiry)?Math.max(0,expiry-now):null;
 const remainingLabel=remaining===null?"Giltighetstid saknas":remaining?`${Math.floor(remaining/86400000)} dygn ${Math.floor(remaining%86400000/3600000)} h ${Math.floor(remaining%3600000/60000)} min`:"Utgången";
 const deadline=Number.isFinite(expiry)?new Date(expiry).toLocaleString("sv-SE",{dateStyle:"short",timeStyle:"short"}):null;
 const mutationsDisabled=busy||loading||!data||statusIssue||writeUncertain;
 const reporterLink=`/reporter?cup=${encodeURIComponent(publicSlug||String(cupId))}`;

 async function changeCode(action:Action){
  if(requestRef.current||!data||statusIssueRef.current||writeUncertainRef.current)return;
  if(action==="rotate"&&active&&!window.confirm("Skapa en ny matchrapportörskod? Den gamla koden och alla aktiva rapportörssessioner slutar fungera direkt."))return;
  if(action==="remove"&&!window.confirm("Ta bort rapportörskoden? Alla aktiva rapportörssessioner slutar fungera."))return;
  const controller=new AbortController();requestRef.current=controller;
  copyIdRef.current+=1;setBusy(true);setError("");setCopied(null);
  const path=`/api/admin/cups/${cupId}/role-codes/reporter${action==="remove"?"":`/${action}`}`;
  const init:RequestInit=action==="remove"?{method:"DELETE"}:{method:"POST",body:JSON.stringify(action==="rotate"?{valid_hours:validHours}:{additional_hours:24})};
  try{
   const status=await req(path,token,controller,init);
   if(requestRef.current!==controller)return;
   setSnapshot({cupId,token,status});
  }catch(reason){
   if(requestRef.current!==controller)return;
   // A transport/5xx failure does not prove the write was rolled back. Only
   // reread status; never repeat a code-changing request automatically.
   const uncertain=!(reason instanceof CodeRequestError)||reason.status>=500||reason.status===408;
   statusIssueRef.current=true;writeUncertainRef.current=uncertain;
   setStatusIssue(true);setWriteUncertain(uncertain);
   setError(uncertain?"Ändringen kunde inte bekräftas. Den kan ha genomförts. Hämta kodstatus igen innan du delar eller ändrar koden.":reason instanceof CodeRequestError&&reason.status===401?"Din adminsession har gått ut. Logga in igen och hämta kodstatus.":"Koden kunde inte ändras. Hämta kodstatus igen och kontrollera att du har behörighet till cupen.");
  }finally{
   if(requestRef.current===controller){requestRef.current=null;setBusy(false);}
  }
 }

 async function copy(kind:"code"|"link"){
  if(kind==="code"&&(!active||!newCode||busy||loading||writeUncertainRef.current))return;
  const copyId=++copyIdRef.current;
  try{
   await navigator.clipboard.writeText(kind==="code"?newCode:publicSiteUrl(reporterLink));
   if(copyIdRef.current!==copyId)return;
   setCopied(kind);
   if(copyTimerRef.current!==null)window.clearTimeout(copyTimerRef.current);
   copyTimerRef.current=window.setTimeout(()=>{if(copyIdRef.current===copyId)setCopied(null);},2000);
  }catch{
   if(copyIdRef.current!==copyId)return;
   setError(kind==="code"?"Koden kunde inte kopieras. Markera och kopiera den manuellt.":"Länken kunde inte kopieras. Öppna rapportörsvyn och kopiera adressen manuellt.");
  }
 }

 const statusLabel=loading?"HÄMTAR":writeUncertain?"ÄNDRING EJ BEKRÄFTAD":statusIssue||!data?"KODSTATUS OKÄND":active?"KOD AKTIV":data.expires_at?"KOD UTGÅNGEN":"INGEN KOD";
 const footer=loading?"Hämtar kodstatus…":writeUncertain?"Hämta kodstatus innan du delar eller ändrar koden.":statusIssue&&data?"Senast hämtad status visas. Hämta kodstatus igen.":!data?"Kodstatus kunde inte hämtas.":deadline?`${active?"Gäller till":"Gick ut"} ${deadline}`:active?"Rapportörskod aktiv.":"Ingen matchrapportörskod skapad ännu.";

 return <section className="admin-panel" id="role-codes" aria-busy={loading||busy}>
  <div className="admin-panel__top"><span>BEHÖRIGHET / MATCHRAPPORTÖR</span><strong>{statusLabel}</strong></div>
  <div className="admin-cupinfo__head"><div><h2>Matchrapportör</h2><p>Ge en funktionär en separat 4-siffrig kod. Den ger bara åtkomst till resultat och matchhändelser – inte cupinställningar.</p></div><span className="admin-lock">BEGRÄNSAD ROLL</span></div>
  {error&&<div className="admin-code-placeholder" role="alert"><b>{writeUncertain?"Ändring ej bekräftad":"Fel"}</b> · {error}{(statusIssue||!data)&&<button type="button" disabled={loading||busy} onClick={()=>void load()}>Hämta kodstatus igen</button>}</div>}
  {!!newCode&&(active||statusIssue||writeUncertain)&&<div className="admin-code-placeholder reporter-admin-code" style={{marginTop:14,textAlign:"center"}}>
   <small>{statusIssue||writeUncertain?"SENAST HÄMTADE RAPPORTÖRSKOD":"AKTIV RAPPORTÖRSKOD"}</small>
   <div style={{fontSize:"2rem",fontWeight:900,letterSpacing:".22em"}}>{newCode}</div>
   <small>{writeUncertain?"Koden kan ha ändrats. Hämta kodstatus igen innan du delar den.":statusIssue?"Senast hämtad kod visas. Hämta status igen för att kontrollera att den fortfarande gäller.":"Samma kod gäller när du återvänder. Att kopiera koden påverkar inga inloggningar."}</small>
  </div>}
  {active&&!statusIssue&&!writeUncertain&&<div className="admin-code-placeholder"><span>Återstår</span><b>{remainingLabel}</b></div>}
  {active&&!newCode&&!statusIssue&&!writeUncertain&&<p className="admin-code-placeholder">Den äldre koden kan inte visas igen. Den fortsätter fungera. Byt kod endast om du behöver en ny; aktiva rapportörer måste då logga in igen.</p>}
  <label style={{display:"grid",gap:6,marginTop:14,maxWidth:280}}><strong>Kodens giltighet från skapandet</strong><select value={validHours} disabled={mutationsDisabled} onChange={event=>setValidHours(Number(event.target.value))}><option value={8}>8 timmar</option><option value={12}>12 timmar</option><option value={24}>1 dygn</option><option value={48}>2 dygn</option><option value={72}>3 dygn</option></select><small>Högst 3 dygn. En inloggning förlänger inte tiden.</small></label>
  <div className="admin-form-footer"><span aria-live="polite">{footer}</span><div className="admin-team-actions">
   {active&&newCode&&<button className="role-code-primary" type="button" disabled={busy||loading||writeUncertain} onClick={()=>void copy("code")}>{copied==="code"?"Kopierat ✓":"Kopiera kod"}</button>}
   <button className={active?"admin-action-secondary":"role-code-primary"} type="button" disabled={mutationsDisabled} onClick={()=>void changeCode("rotate")}>{busy?"Arbetar…":loading?"Hämtar kodstatus…":active?"Byt kod":"Generera 4-siffrig kod"}</button>
   <button type="button" onClick={()=>void copy("link")}>{copied==="link"?"Kopierat ✓":"Kopiera inloggningslänk"}</button>
   <a href={reporterLink} target="_blank" rel="noreferrer">Testa rapportörsvy ↗</a>
   {active&&<><button type="button" disabled={mutationsDisabled} onClick={()=>void changeCode("extend")}>Förläng 24 timmar</button><button type="button" disabled={mutationsDisabled} onClick={()=>void changeCode("remove")}>Ta bort kod</button></>}
  </div></div>
 </section>;
}
