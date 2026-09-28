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

export function CupCover({ tournament, teamCount, matchCount, groupCount }: { tournament: Tournament; teamCount: number; matchCount:number; groupCount:number }) {
  return (
    <header className="cn-cup-cover" aria-labelledby="cup-title">
      <div className="cn-cup-cover__main">
        <p className="cn-cup-cover__label">{tournament.arrangement_type==="matchcamp"?"Matchcamp":"Turnering"}</p>
        <h1 id="cup-title">{tournament.name}</h1>
        <p className="cn-cup-cover__meta"><span>{dateLabel(tournament.start_date)}</span><span>{tournament.arena_address||"Plats kommer"}</span></p>
        {Boolean(tournament.organizer_logos?.length)&&<div className="cn-cup-cover__logos" aria-label="Arrangerande klubbar">{tournament.organizer_logos?.map((logo,index)=><OrganizerLogo key={`${index}-${logo.url}`} name={logo.name} url={logo.url}/>)}</div>}
      </div>
      <div className="cn-cup-cover__stats" aria-label="Cupöversikt">
        <span><b>{teamCount}</b><small>lag</small></span>
        <span><b>{matchCount}</b><small>matcher</small></span>
        {groupCount>0&&<span><b>{groupCount}</b><small>grupper</small></span>}
      </div>
    </header>
  );
}
