"use client";
import { useState } from "react";
import { Tournament } from "@/lib/types";
import { dateLabel } from "@/lib/format";

function OrganizerLogo({name,url}:{name:string;url:string}){
  const [failed,setFailed]=useState(false);
  return <span className="cn-cup-cover__logo" title={name} aria-label={`${name}, arrangör`}>
    {failed?<b aria-hidden="true">{name.slice(0,2).toLocaleUpperCase("sv")}</b>:<img src={url} alt="" width="48" height="48" referrerPolicy="no-referrer" onError={()=>setFailed(true)}/>}
  </span>;
}

export function CupCover({ tournament, teamCount, matchCount, groupCount, publicKey }: { tournament: Tournament; teamCount: number; matchCount:number; groupCount:number; publicKey:string }) {
  const [pdfBusy,setPdfBusy]=useState(false);
  const [pdfError,setPdfError]=useState("");

  async function downloadPdf(){
    if(pdfBusy)return;
    setPdfBusy(true);setPdfError("");
    try{
      const response=await fetch(`/cup/${encodeURIComponent(publicKey)}/pdf`,{cache:"no-store"});
      if(!response.ok)throw new Error(await response.text()||"PDF kunde inte skapas.");
      const blob=await response.blob();
      const filename=response.headers.get("content-disposition")?.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
      const url=URL.createObjectURL(blob);
      const anchor=document.createElement("a");anchor.href=url;anchor.download=filename?decodeURIComponent(filename):"cupnavi.pdf";
      document.body.appendChild(anchor);anchor.click();anchor.remove();
      window.setTimeout(()=>URL.revokeObjectURL(url),60_000);
    }catch(error){setPdfError(error instanceof Error?error.message:"PDF kunde inte skapas. Försök igen.");}
    finally{setPdfBusy(false);}
  }

  return (
    <header className="cn-cup-cover" aria-labelledby="cup-title">
      <div className="cn-cup-cover__main">
        <p className="cn-cup-cover__label">{tournament.arrangement_type==="matchcamp"?"Matchcamp":"Turnering"}</p>
        <h1 id="cup-title">{tournament.name}</h1>
        <p className="cn-cup-cover__meta"><span>{dateLabel(tournament.start_date)}</span><span>{tournament.arena_address||"Plats kommer"}</span></p>
        {Boolean(tournament.organizer_logos?.length)&&<div className="cn-cup-cover__logos" aria-label="Arrangerande klubbar">{tournament.organizer_logos?.map((logo,index)=><OrganizerLogo key={`${index}-${logo.url}`} name={logo.name} url={logo.url}/>)}</div>}
      </div>
      <div className="cn-cup-cover__footer">
        <div className="cn-cup-cover__stats" aria-label="Cupöversikt">
          <span><b>{teamCount}</b><small>lag</small></span>
          <span><b>{matchCount}</b><small>matcher</small></span>
          {groupCount>0&&<span className="cn-cup-cover__group"><b>{groupCount}</b><small>grupper</small></span>}
        </div>
        <div className="cn-cup-cover__extras">
          <button className="cn-cup-cover__pdf" type="button" onClick={()=>void downloadPdf()} disabled={pdfBusy} aria-label={`Skapa och ladda ner PDF för ${tournament.name}`}>{pdfBusy?"Skapar PDF…":"PDF ↓"}</button>
          <nav className="cn-staff-nav" aria-label="Funktionärer"><a href={`/reporter?cup=${encodeURIComponent(publicKey)}`}>Rapportering</a><a href={`/admin?cup=${tournament.id}`}>Admin</a></nav>
        </div>
      </div>
      {pdfError&&<p className="cn-cup-cover__pdf-error" role="alert">{pdfError}</p>}
    </header>
  );
}
