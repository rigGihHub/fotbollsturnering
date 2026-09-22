"use client";

import {useEffect,useState} from "react";
import {readReporterCache} from "../lib/reporter-offline";

type Cup={id:number;public_slug?:string|null};
const cupLink=(cup:Cup)=>`/cup/${encodeURIComponent(cup.public_slug||String(cup.id))}?from=reporter`;

export default function ReporterNavigation({cup}:{cup:Cup|null}){
 const[returnTo,setReturnTo]=useState<string|null>(null);
 useEffect(()=>{
  const query=new URLSearchParams(window.location.search);
  const back=query.get("returnTo");
  if(back){
   try{
    const url=new URL(back,window.location.origin);
    if(url.origin===window.location.origin&&url.pathname.startsWith("/cup/")){
     url.searchParams.set("from","reporter");setReturnTo(url.pathname+url.search);return;
    }
   }catch{/* Fall back to the cup carried by the link or saved session. */}
  }
  const key=query.get("cup");
  if(key){setReturnTo(`/cup/${encodeURIComponent(key)}?from=reporter`);return}
  const cached=readReporterCache<{cup:Cup}>("session");
  if(cached?.cup)setReturnTo(cupLink(cached.cup));
 },[]);
 // Once logged in, the authenticated cup wins over an older incoming link.
 let linkedKey:string|null=null;
 try{linkedKey=returnTo?decodeURIComponent(returnTo.split("?")[0].slice("/cup/".length)):null}catch{/* Ignore malformed incoming paths. */}
 const sameCup=cup&&(linkedKey===cup.public_slug||linkedKey===String(cup.id));
 const target=cup?(sameCup?returnTo:cupLink(cup)):returnTo;
 return <nav className="reporter-navigation" aria-label="Byt vy">
  <a href={target||"/admin"}>{target?"← Turneringsvy":"Välj turnering"}</a>
  <a href="/admin">Admin</a>
 </nav>;
}
