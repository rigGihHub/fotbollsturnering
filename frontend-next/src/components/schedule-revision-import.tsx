"use client";

import { ChangeEvent, useMemo, useState } from "react";
import { CLIENT_API_BASE } from "../lib/client-api";

const API=CLIENT_API_BASE;
type ImportedMatch={time?:string|null;venue?:string|null;group_name?:string|null;home_team?:string|null;away_team?:string|null};
type Proposal={matches?:ImportedMatch[];source_name?:string|null;warnings?:string[]};
type Match={id:number;home_label:string;away_label:string;group_name?:string|null;scheduled_start?:string|null;pitch_number?:number|null;schedule_locked:boolean;played:boolean};
type Schedule={matches:Match[];start_date?:string|null;end_date?:string|null};
type Pitch={pitch_number:number;name:string};
type Venues={pitches:Pitch[]};
type Change={match:Match;nextStart:string;nextPitch:number;source:ImportedMatch;selected:boolean};
type Review={changes:Change[];unchanged:number;unmatched:string[];warnings:string[]};

function norm(value?:string|null){return (value||"").trim().toLocaleLowerCase("sv").replace(/\s+/g," ");}
function startValue(raw:string|undefined|null,schedule:Schedule){
 const value=(raw||"").trim();if(!value)return null;
 if(/^\d{1,2}[:.]\d{2}$/.test(value)){
   if(!schedule.start_date||!schedule.end_date||schedule.start_date!==schedule.end_date)return null;
   return `${schedule.start_date}T${value.replace(".",":").padStart(5,"0")}`;
 }
 const parsed=new Date(value);if(Number.isNaN(parsed.getTime()))return null;
 const date=value.includes("T")?value.slice(0,16):value.replace(" ","T").slice(0,16);
 return date.length>=16?date:null;
}
function pretty(value?:string|null){return value?value.replace("T"," ").slice(0,16):"Ej schemalagd";}

async function json<T>(url:string,token:string,options:RequestInit={}):Promise<T>{
 const headers=new Headers(options.headers||{});headers.set("Authorization",`Bearer ${token}`);if(options.body&&!(options.body instanceof FormData))headers.set("Content-Type","application/json");
 const response=await fetch(`${API}${url}`,{...options,headers,cache:"no-store"});const body=await response.json().catch(()=>null);
 if(!response.ok)throw new Error(body?.detail||`API-fel ${response.status}`);return body as T;
}

export default function ScheduleRevisionImport({token,cupId}:{token:string;cupId:number}){
 const[files,setFiles]=useState<File[]>([]);const[review,setReview]=useState<Review|null>(null);const[busy,setBusy]=useState(false);const[error,setError]=useState("");const[message,setMessage]=useState("");
 const selected=useMemo(()=>review?.changes.filter(row=>row.selected)||[],[review]);
 async function analyze(event?:ChangeEvent<HTMLInputElement>){if(event)setFiles(Array.from(event.target.files||[]));}
 async function readRevision(){
   if(!files.length)return;setBusy(true);setError("");setMessage("");setReview(null);
   try{
     const form=new FormData();files.forEach(file=>form.append("files",file,file.name));
     const [proposal,schedule,venues]=await Promise.all([
       json<Proposal>(`/api/admin/cups/${cupId}/import/revision/analyze`,token,{method:"POST",body:form}),
       json<Schedule>(`/api/admin/cups/${cupId}/schedule`,token),
       json<Venues>(`/api/admin/cups/${cupId}/venues`,token),
     ]);
     const pitchMap=new Map(venues.pitches.map(p=>[norm(p.name),p.pitch_number]));
     const changes:Change[]=[];const unmatched:string[]=[];let unchanged=0;
     for(const imported of proposal.matches||[]){
       const home=norm(imported.home_team),away=norm(imported.away_team),group=norm(imported.group_name);
       if(!home||!away){unmatched.push("En importerad match saknar hemma- eller bortalag.");continue;}
       const candidates=schedule.matches.filter(match=>norm(match.home_label)===home&&norm(match.away_label)===away&&(!group||norm(match.group_name)===group));
       if(candidates.length!==1){unmatched.push(`${imported.home_team} – ${imported.away_team}: ${candidates.length?"flera möjliga matcher":"ingen exakt match hittades"}.`);continue;}
       const match=candidates[0];
       if(match.played||match.schedule_locked){unmatched.push(`${match.home_label} – ${match.away_label}: matchen är ${match.played?"redan spelad":"låst"}.`);continue;}
       const nextStart=startValue(imported.time,schedule);const nextPitch=pitchMap.get(norm(imported.venue));
       if(!nextStart){unmatched.push(`${match.home_label} – ${match.away_label}: datum/tid kan inte bevisas säkert. Flerdagarscuper kräver datum i revisionsunderlaget.`);continue;}
       if(!nextPitch){unmatched.push(`${match.home_label} – ${match.away_label}: planen '${imported.venue||"saknas"}' matchar ingen befintlig plan.`);continue;}
       const currentStart=(match.scheduled_start||"").slice(0,16);
       if(currentStart===nextStart&&Number(match.pitch_number||0)===nextPitch){unchanged++;continue;}
       changes.push({match,nextStart,nextPitch,source:imported,selected:true});
     }
     setReview({changes,unchanged,unmatched,warnings:proposal.warnings||[]});
     if(!changes.length&&!unmatched.length)setMessage("Underlaget innehåller inga schemaändringar jämfört med aktuell cup.");
   }catch(err){setError(err instanceof Error?err.message:"Revisionen kunde inte analyseras.");}finally{setBusy(false);}
 }
 function toggle(id:number){setReview(current=>current?{...current,changes:current.changes.map(row=>row.match.id===id?{...row,selected:!row.selected}:row)}:current);}
 async function apply(){
   if(!review||!selected.length)return;
   if(!window.confirm(`Applicera ${selected.length} granskade schemaändringar?\n\nCupen avpubliceras tills schemat har kontrollerats igen. Om schemat ändrats sedan granskningen stoppas hela importen.`))return;
   setBusy(true);setError("");setMessage("");
   try{
     const changes=selected.map(row=>({match_id:row.match.id,scheduled_start:row.nextStart,pitch_number:row.nextPitch,expected_scheduled_start:row.match.scheduled_start||null,expected_pitch_number:row.match.pitch_number??null}));
     const result=await json<{applied_count:number;conflict_analysis?:{error_count?:number;warning_count?:number}}>(`/api/admin/cups/${cupId}/schedule/revision`,token,{method:"POST",body:JSON.stringify({changes})});
     setMessage(`${result.applied_count} schemaändringar importerades. Konfliktkontroll: ${result.conflict_analysis?.error_count||0} fel och ${result.conflict_analysis?.warning_count||0} varningar.`);setReview(null);setFiles([]);
   }catch(err){setError(err instanceof Error?err.message:"Schemaändringarna kunde inte sparas.");}finally{setBusy(false);}
 }
 return <section className="admin-panel" style={{marginTop:18}}>
   <div className="admin-panel__top"><span>REVISION · FOTO/PDF</span><strong>JÄMFÖR FÖRE SPARA</strong></div>
   <h3>Uppdaterat spelschema</h3><p>Ladda upp ett nytt foto eller dokument efter att cupen redan skapats. CupNavi matchar bara säkra lagpar, visar exakt vad som ändrats och skriver alla godkända ändringar i en enda transaktion.</p>
   <div className="admin-team-editor"><label>Ny version av schema<input type="file" multiple accept=".pdf,.txt,.png,.jpg,.jpeg,.webp,image/*,application/pdf,text/plain" onChange={analyze} disabled={busy}/></label>{files.length>0&&<small>{files.length} filer valda · {files.map(f=>f.name).join(", ")}</small>}<button type="button" onClick={()=>void readRevision()} disabled={busy||!files.length}>{busy?"Analyserar…":"Jämför med aktuellt schema"}</button></div>
   {(error||message)&&<div className="admin-code-placeholder" style={{marginTop:12}}><b>{error?"Fel":"Klart"}</b> · {error||message}</div>}
   {review&&<><div className="admin-dashboard-grid" style={{marginTop:14}}><article className="admin-panel"><strong>{review.changes.length}</strong><small>ändringar</small></article><article className="admin-panel"><strong>{review.unchanged}</strong><small>oförändrade</small></article><article className="admin-panel"><strong>{review.unmatched.length}</strong><small>kräver kontroll</small></article></div>
   {review.changes.length>0&&<div className="admin-team-list" style={{marginTop:12}}>{review.changes.map(row=><article key={row.match.id}><label style={{display:"flex",gap:10,alignItems:"flex-start",width:"100%"}}><input type="checkbox" checked={row.selected} onChange={()=>toggle(row.match.id)}/><span><strong>{row.match.home_label} – {row.match.away_label}</strong><small style={{display:"block"}}>Nu: {pretty(row.match.scheduled_start)} · Plan {row.match.pitch_number||"–"}</small><small style={{display:"block"}}>Nytt: {pretty(row.nextStart)} · Plan {row.nextPitch}</small></span></label></article>)}</div>}
   {review.unmatched.length>0&&<details style={{marginTop:12}} open><summary><strong>Kan inte ändras automatiskt ({review.unmatched.length})</strong></summary><ul>{review.unmatched.map((text,index)=><li key={index}>{text}</li>)}</ul></details>}
   {review.warnings.length>0&&<details style={{marginTop:12}}><summary><strong>Varningar från dokumenttolkningen</strong></summary><ul>{review.warnings.map((text,index)=><li key={index}>{text}</li>)}</ul></details>}
   <div className="admin-form-footer"><span>Osäkra eller låsta matcher lämnas alltid orörda.</span><button type="button" onClick={()=>void apply()} disabled={busy||!selected.length}>{busy?"Sparar…":`Applicera ${selected.length} valda ändringar`}</button></div></>}
 </section>;
}
