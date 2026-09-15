"use client";

import { useState } from "react";
import { CLIENT_API_BASE } from "../lib/client-api";

export default function ExportAdmin({token,cupId}:{token:string;cupId:number}){
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");

  async function downloadPdf(){
    setBusy(true);setError("");
    try{
      const response=await fetch(`${CLIENT_API_BASE}/api/admin/cups/${cupId}/export/pdf`,{headers:{Authorization:`Bearer ${token}`},cache:"no-store"});
      if(!response.ok){const payload=await response.json().catch(()=>null);throw new Error(payload?.detail||`API-fel ${response.status}`);}
      const bytes=await response.arrayBuffer();
      const signature=new TextDecoder("ascii").decode(bytes.slice(0,5));
      if(signature!=="%PDF-")throw new Error("Servern skickade inte en giltig PDF-fil. Försök igen eller kontakta administratören.");
      const blob=new Blob([bytes],{type:"application/pdf"});
      const disposition=response.headers.get("Content-Disposition")||"";
      const match=disposition.match(/filename\*=UTF-8''([^;]+)/i);
      const filename=match?decodeURIComponent(match[1]):`cupnavi-cup-${cupId}.pdf`;
      const url=URL.createObjectURL(blob);
      const anchor=document.createElement("a");anchor.href=url;anchor.download=filename;document.body.appendChild(anchor);anchor.click();anchor.remove();window.setTimeout(()=>URL.revokeObjectURL(url),60_000);
    }catch(reason){setError(reason instanceof Error?reason.message:"PDF-exporten misslyckades.");}
    finally{setBusy(false);}
  }

  return <section className="admin-panel export-console" id="export">
    <div className="publication-console__eyebrow"><span>VERKTYG · PDF & EXPORT</span><strong>FÄRSK DATA</strong></div>
    <div className="export-console__body"><p className="publication-console__kicker">CUPDOKUMENT</p><h2>Ta med cupen</h2><p>Skapa en ny PDF med cupinfo, grupper, lag, planer, schema och resultat. Dokumentet byggs från den aktuella serverdatan när du klickar.</p>{error&&<div className="publication-console__error" role="alert"><strong>PDF kunde inte skapas</strong><span>{error}</span></div>}</div>
    <div className="publication-console__actions"><span>PDF-filen byggs från senast sparade data och kontrolleras före nedladdning.</span><div><button className="admin-action-primary" type="button" onClick={downloadPdf} disabled={busy}>{busy?"Skapar och kontrollerar PDF…":"Skapa och ladda ner PDF"}</button></div></div>
  </section>;
}
