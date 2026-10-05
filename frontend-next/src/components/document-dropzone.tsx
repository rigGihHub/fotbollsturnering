"use client";

import { useRef, useState } from "react";
import styles from "./document-dropzone.module.css";

export function documentFilesError(files:File[]):string {
  if(files.length>12)return "Välj högst 12 filer åt gången.";
  if(files.some(file=>!/^.+\.(pdf|txt|png|jpe?g|webp)$/i.test(file.name)))return "Välj PDF, TXT, PNG, JPG eller WEBP.";
  if(files.some(file=>file.size===0))return "En vald fil är tom. Välj en annan fil.";
  if(files.some(file=>file.size>25*1024*1024))return "En fil är större än 25 MB. Välj en mindre fil.";
  if(files.reduce((sum,file)=>sum+file.size,0)>60*1024*1024)return "Filerna får tillsammans vara högst 60 MB.";
  return "";
}

export default function DocumentDropzone({files,onFiles,disabled=false,buttonLabel="Välj fil"}:{files:File[];onFiles:(files:File[])=>void;disabled?:boolean;buttonLabel?:string}) {
  const input=useRef<HTMLInputElement>(null);
  const [dragging,setDragging]=useState(false);
  const [error,setError]=useState("");
  function choose(next:File[]) {
    if(disabled)return;
    const problem=documentFilesError(next);
    setError(problem);
    if(!problem)onFiles(next);
  }
  return <div className={styles.picker}>
    <div className={`${styles.zone}${dragging?` ${styles.dragging}`:""}`} aria-busy={disabled}
      onDragOver={event=>{event.preventDefault();if(!disabled)setDragging(true);}}
      onDragLeave={event=>{if(!event.currentTarget.contains(event.relatedTarget as Node|null))setDragging(false);}}
      onDrop={event=>{event.preventDefault();setDragging(false);if(event.dataTransfer.files.length)choose(Array.from(event.dataTransfer.files));}}>
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><path d="M7 3h7l4 4v14H7zM14 3v5h4M10 13h5M10 17h5"/></svg>
      <strong>Dra in en ny PDF här</strong>
      <span>eller välj fil från din enhet</span>
      <button type="button" disabled={disabled} onClick={()=>input.current?.click()}>{files.length?"Byt filer":buttonLabel}</button>
      <input ref={input} type="file" multiple hidden accept=".pdf,.txt,.png,.jpg,.jpeg,.webp" aria-label="Nytt cupunderlag" disabled={disabled} onChange={event=>{choose(Array.from(event.target.files||[]));event.target.value="";}}/>
      <small>PDF, bild eller text · högst 25 MB per fil</small>
    </div>
    {files.length>0&&<div className={styles.files}><ul aria-label="Valda filer">{files.map((file,index)=><li key={`${file.name}-${index}`}>{file.name}</li>)}</ul><button type="button" disabled={disabled} onClick={()=>{setError("");onFiles([]);}}>Ta bort filer</button></div>}
    {error&&<p role="alert">{error}</p>}
  </div>;
}
