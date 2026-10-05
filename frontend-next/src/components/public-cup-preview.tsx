"use client";

import { useEffect, useState } from "react";
import { CLIENT_API_BASE } from "@/lib/client-api";
import { CupSnapshot, StandingRow } from "@/lib/types";
import { PLAYOFF_REVIEW_REQUEST_KEY } from "../lib/open-playoff-review";
import { PublicCupView } from "./PublicCupView";

const TOKEN_KEY="cupnavi_admin_session_v629";
type StandingsGroup={group:{id:number;name:string};rows:StandingRow[]};
type PreviewPayload={cup:CupSnapshot;standings:StandingsGroup[];pending_playoff_count?:number};

export default function PublicCupPreview({publicKey,cupId}:{publicKey:string;cupId:number}){
  const [data,setData]=useState<PreviewPayload|null>(null);
  const [error,setError]=useState("");
  const[retry,setRetry]=useState(0);
  useEffect(()=>{
    setError("");
    setData(null);
    const token=localStorage.getItem(TOKEN_KEY);
    if(!token){setError("Adminsessionen saknas. Logga in igen för att förhandsgranska utkastet.");return;}
    const controller=new AbortController();
    fetch(`${CLIENT_API_BASE}/api/admin/cups/${cupId}/preview`,{headers:{Authorization:`Bearer ${token}`},cache:"no-store",signal:controller.signal})
      .then(async response=>{const payload=await response.json().catch(()=>null);if(!response.ok)throw new Error(payload?.detail||"Förhandsgranskningen kunde inte hämtas.");return payload as PreviewPayload;})
      .then(setData).catch(reason=>{if(reason?.name!=="AbortError")setError(reason instanceof Error?reason.message:"Förhandsgranskningen kunde inte hämtas.");});
    return()=>controller.abort();
  },[cupId,retry]);
  if(error)return <main className="page-shell"><article className="empty-state"><strong>Turneringsvyn kunde inte öppnas</strong><p>{error}</p><a href="/admin">Tillbaka till admin</a></article></main>;
  if(!data)return <main className="page-shell"><article className="empty-state"><strong>Öppnar turneringsvyn…</strong><p>CupNavi hämtar utkastet utan att publicera det.</p></article></main>;
  return <><div className="preview-ribbon" style={{display:"flex",justifyContent:"center",alignItems:"center",gap:12,flexWrap:"wrap",fontSize:14,letterSpacing:0}}>Adminförhandsgranskning {!data.cup.tournament.is_published&&"· UTKAST"} <button style={{minHeight:44,padding:"8px 12px",fontSize:14}} type="button" onClick={()=>setRetry(value=>value+1)}>Uppdatera vyn</button></div>{!!data.pending_playoff_count&&<article className="empty-state"><strong>{data.pending_playoff_count} slutspelsmatcher väntar på godkännande</strong><p>Matchraderna finns i importunderlaget men är ännu inte skapade i cupen.</p><a href={`/admin?cup=${cupId}#playoffs`} onClick={()=>{try{sessionStorage.setItem(PLAYOFF_REVIEW_REQUEST_KEY,String(cupId));}catch{}}}>Granska och skapa slutspelet</a></article>}<PublicCupView key={`${cupId}-${retry}`} previewMode publicKey={publicKey} initialCup={data.cup} initialStandings={data.standings||[]}/></>;
}
