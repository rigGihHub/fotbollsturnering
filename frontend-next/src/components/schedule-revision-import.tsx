"use client";

import { useMemo, useState } from "react";
import { CLIENT_API_BASE } from "../lib/client-api";
import DocumentDropzone from "./document-dropzone";
import { reviewScheduleRevision, type RevisionProposal, type RevisionSchedule, type RevisionPitch, type RevisionReview } from "../lib/schedule-revision-review";
import { revisionCommitRows, revisionIsSaved } from "../lib/schedule-revision-commit";

const API=CLIENT_API_BASE;
type Venues={pitches:RevisionPitch[]};
function pretty(value?:string|null){return value?value.replace("T"," ").slice(0,16):"Ej schemalagd";}

async function json<T>(url:string,token:string,options:RequestInit={}):Promise<T>{
 const headers=new Headers(options.headers||{});headers.set("Authorization",`Bearer ${token}`);if(options.body&&!(options.body instanceof FormData))headers.set("Content-Type","application/json");
 const response=await fetch(`${API}${url}`,{...options,headers,cache:"no-store"});const body=await response.json().catch(()=>null);
 if(!response.ok)throw new Error(body?.detail||`API-fel ${response.status}`);return body as T;
}

export default function ScheduleRevisionImport({token,cupId,cupName,onImported}:{token:string;cupId:number;cupName?:string;onImported?:()=>void|Promise<void>}){
 const[files,setFiles]=useState<File[]>([]);const[review,setReview]=useState<RevisionReview|null>(null);const[pitches,setPitches]=useState<RevisionPitch[]>([]);const[operation,setOperation]=useState<"idle"|"compare"|"save">("idle");const[error,setError]=useState("");const[message,setMessage]=useState("");const[compareFailed,setCompareFailed]=useState(false);
 const busy=operation!=="idle";
 const selected=useMemo(()=>review?.changes.filter(row=>row.selected)||[],[review]);
 function choose(next:File[]){setFiles(next);setReview(null);setError("");setMessage("");setCompareFailed(false);}
 const pitchName=(number?:number|null)=>pitches.find(p=>p.pitch_number===number)?.name||`Plan ${number||"–"}`;
 async function readRevision(){
   if(!files.length)return;setOperation("compare");setError("");setMessage("");setCompareFailed(false);
   try{
     const form=new FormData();files.forEach(file=>form.append("files",file,file.name));
     const [proposal,schedule,venues]=await Promise.all([
       json<RevisionProposal>(`/api/admin/cups/${cupId}/import/revision/analyze`,token,{method:"POST",body:form}),
       json<RevisionSchedule>(`/api/admin/cups/${cupId}/schedule`,token),
       json<Venues>(`/api/admin/cups/${cupId}/venues`,token),
     ]);
     const comparison=reviewScheduleRevision(proposal,schedule,venues.pitches);
     setPitches(venues.pitches);
     setReview(comparison);
     if(!schedule.matches.length)setMessage("Cupen saknar matcher. Öppna Komplettera cupens underlag nedan för att läsa in ett första matchprogram.");
     else if(!proposal.matches?.length)setMessage("Inga matcher kunde läsas ur underlaget. Prova en PDF med spelschemat eller en tydlig bild.");
     else if(!comparison.changes.length&&!comparison.unmatched.length)setMessage(`Inga ändringar som kan sparas hittades.${comparison.unchanged?` ${comparison.unchanged} matcher har redan samma tid och plan.`:""}${comparison.preserved.length?` ${comparison.preserved.length} spelade eller låsta matcher bevaras.`:""}`);
   }catch(err){setCompareFailed(true);setError(`${err instanceof Error?err.message:"Filen kunde inte läsas just nu. Försök jämföra igen."}${review?" Den senaste granskningen och dina val visas fortfarande.":""}`);}finally{setOperation("idle");}
 }
 function toggle(id:number){setReview(current=>current?{...current,changes:current.changes.map(row=>row.match.id===id?{...row,selected:!row.selected}:row)}:current);}
 async function apply(){
   if(!review||!selected.length)return;
   setOperation("save");setError("");setMessage("");
   try{
     const changes=revisionCommitRows(selected);
     const result=await json<{applied_count:number;schedule?:RevisionSchedule;conflict_analysis?:{error_count?:number;warning_count?:number}}>(`/api/admin/cups/${cupId}/schedule/revision`,token,{method:"POST",body:JSON.stringify({changes})});
     const saved=result.schedule||await json<RevisionSchedule>(`/api/admin/cups/${cupId}/schedule`,token);
     if(result.applied_count!==selected.length||!revisionIsSaved(selected,saved))throw new Error("Servern kunde inte bekräfta alla sparade tider och planer. Kontrollera schemat och jämför igen innan du gör ett nytt försök.");
     setMessage(`${result.applied_count} schemaändringar är genomförda och sparade i ${cupName||"cupen"}. Cupen är avpublicerad. Kontrollera schemat och publicera igen. Konfliktkontroll: ${result.conflict_analysis?.error_count||0} fel och ${result.conflict_analysis?.warning_count||0} varningar.`);setReview(null);setFiles([]);setCompareFailed(false);
     window.dispatchEvent(new Event("cupnavi:session-refresh"));
     try{await onImported?.();}catch{setMessage(current=>`${current} Vyn kunde inte uppdateras automatiskt. Öppna Schema för att se ändringarna.`);}
   }catch(err){setError(err instanceof Error?err.message:"Schemaändringarna kunde inte sparas.");}finally{setOperation("idle");}
 }
 return <section className="admin-panel import-update-card" id="pdf-cup-update" aria-busy={busy}>
   <div className="admin-panel__top"><span>UPPDATERA BEFINTLIG CUP</span><strong>PDF · BILD</strong></div>
   <h2>Uppdatera med ny PDF</h2><p>Jämför nya matchtider och planer med <strong>{cupName||"aktiv cup"}</strong>. Granska ändringarna och genomför dem för att uppdatera cupens schema.</p>
   <DocumentDropzone files={files} onFiles={choose} disabled={busy}/>
   <div className="admin-form-footer"><span>{operation==="save"?"Sparar valda ändringar…":busy?"Läser filen och jämför med schemat…":"1. Välj fil · 2. Jämför · 3. Genomför valda ändringar"}</span><button type="button" onClick={()=>void readRevision()} style={review?{background:"white",color:"#16333b"}:undefined} disabled={busy||!files.length}>{operation==="save"?"Sparar…":busy?"Jämför…":compareFailed?"Försök jämföra igen":"Jämför med aktuellt schema"}</button></div>
   {(error||message)&&<div className="admin-code-placeholder" style={{marginTop:12,display:"block"}} role={error?"alert":"status"}><b>{error?"Kunde inte slutföra":"Granskning"}</b> · {error||message}{message&&!review&&<p><a href="#schedule">Kontrollera schemat →</a></p>}</div>}
   {error&&<p><a href="#schedule">Öppna schemat och kontrollera aktuella tider →</a></p>}
   {review?.extractionMethod==="pdf_text"&&<p role="status" style={{marginTop:14}}>Matchrader lästes från dokumentets text utan AI. Endast de visade matchradernas tider och planer jämförs. Kontrollera även rader som kräver kontroll.</p>}
   {review&&<>{review.changes.length>0&&<p role="status" style={{marginTop:14}}><strong>{review.changes.length} ändringar hittades.</strong> De är inte genomförda ännu. {selected.length} är valda för att uppdatera schemat.</p>}<div className="cup-import-stats" style={{marginTop:14}}><div><strong>{review.changes.length}</strong><small>ändringar</small></div><div><strong>{review.unchanged}</strong><small>oförändrade</small></div><div><strong>{review.unmatched.length}</strong><small>kräver kontroll</small></div><div><strong>{review.preserved.length}</strong><small>bevaras</small></div></div>
   {review.changes.length>0&&<div className="admin-team-list" style={{marginTop:12}}>{review.changes.map(row=><article key={row.match.id}><label style={{display:"flex",gap:10,alignItems:"flex-start",width:"100%"}}><input type="checkbox" checked={row.selected} disabled={busy} onChange={()=>toggle(row.match.id)}/><span><strong>{row.match.home_label} – {row.match.away_label}</strong><small style={{display:"block"}}>Nuvarande: {pretty(row.match.scheduled_start)} · {pitchName(row.match.pitch_number)}</small><small style={{display:"block"}}>Från PDF: {pretty(row.nextStart)} · {pitchName(row.nextPitch)}</small>{row.matchingNote&&<small style={{display:"block",marginTop:6}}>{row.matchingNote}</small>}</span></label></article>)}</div>}
   {review.unmatched.length>0&&<details style={{marginTop:12}} open><summary><strong>Kan inte ändras automatiskt ({review.unmatched.length})</strong></summary><ul>{review.unmatched.map((text,index)=><li key={index}>{text}</li>)}</ul></details>}
   {review.preserved.length>0&&<details style={{marginTop:12}}><summary><strong>Spelade eller låsta matcher bevaras ({review.preserved.length})</strong></summary><ul>{review.preserved.map((text,index)=><li key={index}>{text}</li>)}</ul></details>}
   {review.warnings.length>0&&<details style={{marginTop:12}}><summary><strong>Noteringar från PDF:en</strong></summary><ul>{review.warnings.map((text,index)=><li key={index}>{text}</li>)}</ul></details>}
   <div className="admin-form-footer"><span>När du sparar ändringarna avpubliceras cupen. Kontrollera schemat och publicera igen.</span><button type="button" onClick={()=>void apply()} disabled={busy||!selected.length}>{operation==="save"?"Genomför ändringarna…":`Genomför ${selected.length} valda ändringar`}</button></div></>}
 </section>;
}
