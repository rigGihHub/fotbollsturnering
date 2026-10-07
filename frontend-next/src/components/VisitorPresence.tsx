"use client";
import {useEffect,useState} from "react";
import {startVisitorPresence} from "../lib/visitor-presence";

export function VisitorPresence({publicKey,enabled=true}:{publicKey:string;enabled?:boolean}) {
  const [count,setCount]=useState<number|null>(null);
  useEffect(()=>{
    setCount(null);
    if(!enabled)return;
    return startVisitorPresence(publicKey,setCount);
  },[publicKey,enabled]);
  if(!enabled)return null;
  const label=count===null?"Besökarantalet är inte tillgängligt ännu":`${count} aktiva webbläsare just nu`;
  return <span className="cn-visitors" role="img" aria-label={label} title={`${label}. Aktiv betyder att cupen varit synlig under de senaste 90 sekunderna.`}>
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true" focusable="false"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>
    <span aria-hidden="true">{count===null?"—":new Intl.NumberFormat("sv-SE").format(count)}</span>
  </span>;
}
