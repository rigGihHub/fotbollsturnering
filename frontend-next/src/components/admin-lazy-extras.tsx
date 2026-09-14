"use client";

import { useEffect, useState } from "react";
import PitchWindowImportReview from "./pitch-window-import-review";
import PlayoffImportReview from "./playoff-import-review";
import ImportCompletionSummary from "./import-completion-summary";

type Step = "venues"|"schedule"|"playoffs"|"import"|"other";

function currentStep():Step {
  const value=window.location.hash.replace(/^#/,"");
  if(value==="venues"||value==="schedule"||value==="playoffs"||value==="import")return value;
  return "other";
}

export default function AdminLazyExtras() {
  const [step,setStep]=useState<Step>("other");

  useEffect(()=>{
    const sync=()=>setStep(currentStep());
    const onStep=(event:Event)=>{
      const value=(event as CustomEvent<string>).detail;
      if(value==="venues"||value==="schedule"||value==="playoffs"||value==="import")setStep(value);
      else setStep("other");
    };
    sync();
    window.addEventListener("hashchange",sync);
    window.addEventListener("cupnavi:admin-step",onStep);
    return()=>{
      window.removeEventListener("hashchange",sync);
      window.removeEventListener("cupnavi:admin-step",onStep);
    };
  },[]);

  return <>
    {(step==="venues"||step==="schedule"||step==="import") && <PitchWindowImportReview/>}
    {(step==="playoffs"||step==="import") && <PlayoffImportReview/>}
    {step==="import" && <ImportCompletionSummary/>}
  </>;
}
