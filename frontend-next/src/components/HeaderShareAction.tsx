"use client";

import { usePathname } from "next/navigation";
import { useState } from "react";
import { publicCupUrl } from "../lib/public-site-url";
import { cupShareTitle } from "../lib/cup-share-title";

export function HeaderShareAction(){
  const pathname=usePathname();
  const [label,setLabel]=useState("Dela cupen");
  if(!pathname.startsWith("/cup/"))return null;

  const share=async()=>{
    const url=publicCupUrl(pathname);
    const name=document.getElementById("cup-title")?.textContent;
    const title=cupShareTitle(name);
    try{
      if(navigator.share){await navigator.share({title,text:title,url});setLabel("Delad ✓");return;}
      await navigator.clipboard.writeText(`${title}\n${url}`);setLabel("Kopierat ✓");
    }catch{setLabel("Dela cupen");}
  };

  return <button type="button" className="header-share-action" onClick={()=>void share()}><span aria-hidden="true">↗</span>{label}</button>;
}
