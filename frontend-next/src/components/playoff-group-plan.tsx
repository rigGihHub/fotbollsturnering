"use client";

import { useState } from "react";
import DocumentDropzone from "./document-dropzone";
import { CLIENT_API_BASE } from "../lib/client-api";
import styles from "./playoff-admin.module.css";

const FORMAT="Nytt gruppspel – lag med samma placering";
type Row={label:string;home_source:string;away_source:string;time?:string|null;venue?:string|null;duration?:string|null};
type Preview={cup_name:string;revision:string;source_name?:string|null;replaced_count:number;locked_time_count:number;match_count:number;scheduled_count:number;matches:Row[];levels:{name:string;placement:number;participant_count:number;matches:Row[]}[]};
async function request<T>(path:string,token:string,body?:unknown):Promise<T>{
 const headers=new Headers({Authorization:`Bearer ${token}`});if(body&&!(body instanceof FormData))headers.set("Content-Type","application/json");
 const response=await fetch(`${CLIENT_API_BASE}${path}`,{method:body?"POST":"GET",headers,body:body instanceof FormData?body:body?JSON.stringify(body):undefined,cache:"no-store"});
 const result=await response.json().catch(()=>null);if(!response.ok)throw new Error(result?.detail||`API-fel ${response.status}`);return result as T;
}

export default function PlayoffGroupPlan({token,cupId,cupName,blocked,working,onWorking,onApplied}:{token:string;cupId:number;cupName?:string;blocked:boolean;working:boolean;onWorking:(busy:boolean)=>void;onApplied:()=>void|Promise<void>}){
 const[open,setOpen]=useState(false);const[format,setFormat]=useState("");const[files,setFiles]=useState<File[]>([]);const[useSaved,setUseSaved]=useState(true);const[preview,setPreview]=useState<Preview|null>(null);const[localBusy,setLocalBusy]=useState(false);const[error,setError]=useState("");const[message,setMessage]=useState("");
 const busy=localBusy||working;
 function setBusy(value:boolean){setLocalBusy(value);onWorking(value);}
 function choose(next:File[]){setFiles(next);setPreview(null);setError("");setMessage("");}
 async function compare(){
  if(!format)return;setBusy(true);setError("");setMessage("");setPreview(null);
  try{
   let source_rows:Row[]|undefined=useSaved?undefined:[],source_name:string|undefined;
   if(files.length){const form=new FormData();files.forEach(file=>form.append("files",file,file.name));const proposal=await request<{playoff_matches?:Row[];source_name?:string}>(`/api/admin/cups/${cupId}/import/revision/analyze`,token,form);source_rows=proposal.playoff_matches;source_name=proposal.source_name;if(!source_rows?.length)throw new Error("Inga slutspelsmatcher kunde läsas ur PDF:en. Prova en PDF med placeringsgruppernas matcher.");}
   setPreview(await request<Preview>(`/api/admin/cups/${cupId}/playoffs/group-plan/preview`,token,{source_rows,source_name}));
  }catch(err){setError(err instanceof Error?err.message:"Upplägget kunde inte förhandsgranskas.");}finally{setBusy(false);}
 }
 async function apply(){
  if(!preview)return;setBusy(true);setError("");
  try{
   const result=await request<{placement_mode:boolean;match_count:number}>(`/api/admin/cups/${cupId}/playoffs/group-plan/apply`,token,{revision:preview.revision,source_rows:preview.matches,source_name:preview.source_name});
   if(!result.placement_mode||result.match_count!==preview.match_count)throw new Error("Servern kunde inte bekräfta hela det nya gruppspelet. Öppna Slutspel igen och kontrollera utfallet.");
   setMessage(`${result.match_count} matcher i det nya gruppspelet är sparade. Cupen är avpublicerad. Kontrollera schemat före publicering.`);setPreview(null);setFiles([]);setOpen(false);
   window.dispatchEvent(new Event("cupnavi:session-refresh"));try{await onApplied();}catch{setMessage("Det nya gruppspelet är sparat. Ladda om sidan för att hämta det senaste upplägget.");}
  }catch(err){setError(err instanceof Error?err.message:"Upplägget kunde inte sparas.");}finally{setBusy(false);}
 }
 return <section className={styles.plan}>
  <div className="admin-form-footer"><span>Nytt gruppspel samlar lag med samma placering i egna grupper.</span><button className={styles.secondary} type="button" disabled={blocked||busy} onClick={()=>{setOpen(!open);setError("");}}>{open?"Stäng formatval":"Byt slutspelsformat"}</button></div>
  {blocked&&<p>Slutspelet har startats eller har resultat. Formatbyte är därför låst.</p>}
  {(error||message)&&<p role={error?"alert":"status"}>{error||message} <a href="#schedule">Kontrollera schemat</a></p>}
  {open&&<><h3>Nytt slutspel för {cupName||"aktiv cup"}</h3><label>Välj slutspelsformat<select value={format} disabled={busy} onChange={e=>{setFormat(e.target.value);setPreview(null);}}><option value="">Välj format…</option><option value={FORMAT}>{FORMAT}</option></select></label>
   <p className={styles.explanation}>Ettorna möts i Guld, tvåorna i Silver och treorna i Brons. Finns fler placeringar får även de egna grupper. Alla lag i varje nivå möter varandra en gång. Matcherna får sluta oavgjort och tabell avgör placeringen. Matchlängden kontrolleras separat under Regler.</p>
   <label style={{display:"flex",alignItems:"center",gap:10}}><input type="checkbox" checked={useSaved} disabled={busy||files.length>0} onChange={e=>{setUseSaved(e.target.checked);setPreview(null);}}/> Behåll tider från befintligt gruppspel eller redan inläst underlag</label>
   <details><summary>Behåll tider och planer från en PDF</summary><p>Underlaget måste ha samma grundgrupper och placeringar som {cupName||"aktiv cup"}. Lag och grundgrupper läggs inte till vid formatbytet.</p><DocumentDropzone files={files} onFiles={choose} disabled={busy}/></details>
   {!preview&&<div className="admin-form-footer"><span>{files.length?files.map(f=>f.name).join(", "):useSaved?"Befintliga placeringsmatcher eller sparat PDF-underlag används när det finns.":"Nya matcher skapas utan tid. Planera dem under Schema."}</span><button type="button" disabled={busy||!format} onClick={()=>void compare()}>{busy?"Förhandsgranskar…":"Förhandsgranska nytt slutspel"}</button></div>}
   {preview&&<><p><strong>{preview.cup_name}</strong> · {preview.source_name||"Förslag från cupens grundgrupper"}</p><p>{preview.replaced_count} ospelade slutspelsmatcher ersätts med <strong>{preview.match_count} nya matcher</strong>. {preview.scheduled_count} tider och planer från underlaget behålls. {preview.match_count-preview.scheduled_count>0&&`${preview.match_count-preview.scheduled_count} matcher behöver schemaläggas.`}</p>{preview.locked_time_count>0&&<p>{preview.locked_time_count} befintliga matcher har tidslås och ersätts också. Tider förs endast över från PDF-rader med samma deltagarkällor.</p>}
   <div className={styles.brackets}>{preview.levels.map(level=><article className={styles.bracket} key={level.placement}><header className={styles.bracketHeader}><strong>{level.name}</strong><small>{level.participant_count} lag · {level.matches.length} matcher · alla möter alla</small></header>{level.matches.map((row,index)=><div className={styles.match} key={index}><div className={styles.matchDetails}><strong>{row.home_source} – {row.away_source}</strong><small>{row.time?.replace("T"," ")||"Tid behöver planeras"}{row.venue?` · ${row.venue}`:""}</small></div></div>)}</article>)}</div>
   <p className={styles.explanation}>Grundgruppernas matcher och resultat behålls. Cupen avpubliceras efter bytet. Det tidigare slutspelsupplägget sparas och kan återställas tills det nya har ändrats eller startats.</p><div className="admin-form-footer"><button className={styles.secondary} type="button" disabled={busy} onClick={()=>setPreview(null)}>Ändra förslaget</button><button type="button" disabled={busy} onClick={()=>void apply()}>{busy?"Sparar…":`Ersätt slutspelet med ${preview.match_count} nya matcher`}</button></div></>}
  </>}
 </section>;
}
