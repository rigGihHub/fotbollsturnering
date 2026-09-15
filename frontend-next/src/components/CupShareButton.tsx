"use client";

import { useState } from "react";

export function CupShareButton({cupName}:{cupName:string}){
  const [label,setLabel]=useState("Dela cupen");
  const share=async()=>{
    const url=window.location.href.split("?")[0];
    try{
      if(navigator.share){await navigator.share({title:cupName,text:`Följ ${cupName} i CupNavi`,url});setLabel("Delad ✓");return;}
      await navigator.clipboard.writeText(url);setLabel("Länk kopierad ✓");
    }catch{setLabel("Dela cupen");}
  };
  return <button type="button" className="cup-cover__share" onClick={()=>void share()}><span aria-hidden="true">↗</span>{label}</button>;
}
