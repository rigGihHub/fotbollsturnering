"use client";

import { usePathname } from "next/navigation";
import { useState } from "react";

export function HeaderShareAction(){
  const pathname=usePathname();
  const [label,setLabel]=useState("Dela cupen");
  if(!pathname.startsWith("/cup/"))return null;

  const share=async()=>{
    const url=new URL(pathname,window.location.origin).toString();
    try{
      if(navigator.share){await navigator.share({title:document.title,url});setLabel("Delad ✓");return;}
      await navigator.clipboard.writeText(url);setLabel("Länk kopierad ✓");
    }catch{setLabel("Dela cupen");}
  };

  return <button type="button" className="header-share-action" onClick={()=>void share()}><span aria-hidden="true">↗</span>{label}</button>;
}
