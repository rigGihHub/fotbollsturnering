"use client";

import { useEffect, useState } from "react";
import { CLIENT_API_BASE } from "@/lib/client-api";
import { CupSnapshot, StandingRow } from "@/lib/types";
import { PublicCupView } from "./PublicCupView";

const TOKEN_KEY="cupnavi_admin_session_v629";
type StandingsGroup={group:{id:number;name:string};rows:StandingRow[]};
type PreviewPayload={cup:CupSnapshot;standings:StandingsGroup[]};

export default function PublicCupPreview({publicKey,cupId}:{publicKey:string;cupId:number}){
  const [data,setData]=useState<PreviewPayload|null>(null);
  const [error,setError]=useState("");
  useEffect(()=>{
    const token=localStorage.getItem(TOKEN_KEY);
    if(!token){setError("Adminsessionen saknas. Logga in igen för att förhandsgranska utkastet.");return;}
    const controller=new AbortController();
    fetch(`${CLIENT_API_BASE}/api/admin/cups/${cupId}/preview`,{headers:{Authorization:`Bearer ${token}`},cache:"no-store",signal:controller.signal})
      .then(async response=>{const payload=await response.json().catch(()=>null);if(!response.ok)throw new Error(payload?.detail||"Förhandsgranskningen kunde inte hämtas.");return payload as PreviewPayload;})
      .then(setData).catch(reason=>{if(reason?.name!=="AbortError")setError(reason instanceof Error?reason.message:"Förhandsgranskningen kunde inte hämtas.");});
    return()=>controller.abort();
  },[cupId]);
  if(error)return <main className="page-shell"><article className="empty-state"><strong>Turneringsvyn kunde inte öppnas</strong><p>{error}</p><a href="/admin">Tillbaka till admin</a></article></main>;
  if(!data)return <main className="page-shell"><article className="empty-state"><strong>Öppnar turneringsvyn…</strong><p>CupNavi hämtar utkastet utan att publicera det.</p></article></main>;
  return <>{!data.cup.tournament.is_published&&<div className="preview-ribbon">FÖRHANDSGRANSKNING · UTKAST</div>}<PublicCupView publicKey={publicKey} initialCup={data.cup} initialStandings={data.standings||[]}/></>;
}
