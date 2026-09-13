"use client";
import {useEffect,useMemo,useState} from "react";
import {CLIENT_API_BASE} from "../lib/client-api";
const API=CLIENT_API_BASE;
const TOKEN_KEY="cupnavi_admin_session_v629";
const CUP_KEY="cupnavi_admin_active_cup_v651";
const GUIDE_KEY="cupnavi_setup_guide_step_v1";
type Session={account?:{role?:string|null;is_owner?:boolean};cups?:Array<{id:number;name:string}>};
type Counts={teams:number;groups:number};
const steps=[
 {title:"Cupinfo",text:"Kontrollera namn, datum, arrangör, spelplats och kontaktuppgifter.",href:"#cupinfo"},
 {title:"Lag",text:"Lägg till lagen – eller använd bild/PDF-importen om du redan har ett underlag.",href:"#teams"},
 {title:"Grupper",text:"Skapa grupper och placera lagen rätt.",href:"#groups"},
 {title:"Planer & tider",text:"Ange planer och när de faktiskt är tillgängliga.",href:"#venues"},
 {title:"Regler",text:"Sätt matchtid, pauser, poängregler och slutspelsregler.",href:"#rules"},
 {title:"Schema",text:"Skapa eller importera schemat och rätta alla krockar.",href:"#schedule"},
 {title:"Slutspel",text:"Bygg slutspel och kontrollera att källorna till varje match är rätt.",href:"#playoffs"},
 {title:"Kontroll",text:"Gå igenom CupNavis varningar. Inget viktigt ska döljas eller gissas.",href:"#publish"},
 {title:"Publicera",text:"Förhandsgranska cupen och publicera först när allt ser rätt ut.",href:"#publish"},
];
async function getJson<T>(path:string,token:string):Promise<T>{const r=await fetch(`${API}${path}`,{headers:{Authorization:`Bearer ${token}`},cache:"no-store"});const p=await r.json().catch(()=>null);if(!r.ok)throw new Error(p?.detail||`API-fel ${r.status}`);return p as T}
export default function CupSetupGuide(){
 const[visible,setVisible]=useState(false),[available,setAvailable]=useState(false),[cupName,setCupName]=useState("Cup"),[step,setStep]=useState(0),[counts,setCounts]=useState<Counts|null>(null);
 useEffect(()=>{const token=localStorage.getItem(TOKEN_KEY);if(!token)return;void getJson<Session>("/api/admin/session",token).then(async s=>{const owner=s.account?.role==="owner"||s.account?.is_owner===true;if(!owner)return;const params=new URLSearchParams(window.location.search);const requested=Number(params.get("cup"))||Number(localStorage.getItem(CUP_KEY));const cup=(s.cups||[]).find(c=>c.id===requested)||(s.cups||[])[0];if(!cup)return;setAvailable(true);setCupName(cup.name);const saved=Math.max(0,Math.min(steps.length-1,Number(localStorage.getItem(`${GUIDE_KEY}:${cup.id}`))||0));setStep(saved);if(params.get("guide")==="1")setVisible(true);try{const[t,g]=await Promise.all([getJson<{teams:unknown[]}>(`/api/admin/cups/${cup.id}/teams`,token),getJson<{groups:unknown[]}>(`/api/admin/cups/${cup.id}/groups`,token)]);setCounts({teams:t.teams?.length||0,groups:g.groups?.length||0})}catch{} }).catch(()=>undefined)},[]);
 const progress=useMemo(()=>Math.round(((step+1)/steps.length)*100),[step]);
 function select(next:number){const n=Math.max(0,Math.min(steps.length-1,next));setStep(n);const cupId=Number(new URLSearchParams(window.location.search).get("cup"))||Number(localStorage.getItem(CUP_KEY));if(cupId)localStorage.setItem(`${GUIDE_KEY}:${cupId}`,String(n))}
 function go(){const target=document.querySelector(steps[step].href);if(target)target.scrollIntoView({behavior:"smooth",block:"start"});else window.location.hash=steps[step].href}
 function close(){setVisible(false);const u=new URL(window.location.href);u.searchParams.delete("guide");window.history.replaceState({},"",`${u.pathname}${u.search}${u.hash}`)}
 if(!available)return null;
 if(!visible)return <button type="button" className="cup-setup-guide-launch" onClick={()=>setVisible(true)}>☰ Cupguide</button>;
 return <aside className="cup-setup-guide" aria-label="Guide för att skapa cup"><div className="cup-setup-guide__head"><div><span>CUPGUIDE · {step+1}/{steps.length}</span><strong>{cupName}</strong></div><button type="button" onClick={close}>Stäng</button></div><div className="cup-setup-guide__body"><div className="cup-setup-guide__progress" aria-label={`${progress} procent klart`}><span style={{width:`${progress}%`}}/></div><div className="cup-setup-guide__step"><span className="cup-setup-guide__number">{String(step+1).padStart(2,"0")}</span><div><h3>{steps[step].title}</h3><p>{steps[step].text}</p>{step===1&&counts&&<p><strong>{counts.teams}</strong> lag registrerade.</p>}{step===2&&counts&&<p><strong>{counts.groups}</strong> grupper registrerade.</p>}</div></div><div className="cup-setup-guide__actions"><button type="button" disabled={step===0} onClick={()=>select(step-1)}>← Föregående</button><button type="button" className="is-primary" onClick={go}>Öppna steget</button><button type="button" disabled={step===steps.length-1} onClick={()=>select(step+1)}>Nästa →</button></div></div></aside>;
}
