"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { CupNaviApiError, getCup } from "@/lib/api";
import { PublicCupView } from "@/components/PublicCupView";

const RETRY_DELAYS=[2000,5000,10000,30000];

export default function PublicCupRecovery({publicKey,reporterReturn=false}:{publicKey:string;reporterReturn?:boolean}){
  const [cup,setCup]=useState<Awaited<ReturnType<typeof getCup>>|null>(null);
  const [attempt,setAttempt]=useState(0);
  const [waiting,setWaiting]=useState(true);
  const [missingCount,setMissingCount]=useState(0);
  const timer=useRef<number|undefined>(undefined);

  const load=useCallback(async()=>{
    setWaiting(true);
    try{
      setCup(await getCup(publicKey));
      setMissingCount(0);
    }catch(error){
      setMissingCount(count=>error instanceof CupNaviApiError&&error.status===404?count+1:0);
      setWaiting(false);
      setAttempt(value=>value+1);
    }
  },[publicKey]);

  useEffect(()=>{
    const delay=RETRY_DELAYS[Math.min(attempt,RETRY_DELAYS.length-1)];
    timer.current=window.setTimeout(()=>void load(),delay);
    return()=>{if(timer.current)window.clearTimeout(timer.current)};
  },[attempt,load]);

  if(cup)return <PublicCupView publicKey={publicKey} initialCup={cup} initialStandings={[]} reporterReturn={reporterReturn}/>;
  const missing=missingCount>=3;
  return <main className="page-shell"><section className="status-page public-cup-recovery" aria-live="polite">
    <span>{missing?"CUPEN HITTADES INTE":"ÖPPNAR CUPEN"}</span>
    <h1>{missing?"Kontrollera cupens länk.":"Cupen är snart klar."}</h1>
    <p>{missing?"Cupen kan vara avpublicerad eller länken kan vara fel.":waiting?"Matcher, tabeller och resultat hämtas.":"Det tar längre tid än vanligt. CupNavi försöker igen automatiskt."}</p>
    <div><button type="button" disabled={waiting} onClick={()=>{if(timer.current)window.clearTimeout(timer.current);void load()}}>{waiting?"Hämtar…":"Försök nu"}</button></div>
  </section></main>;
}
