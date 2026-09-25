"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { adminPhase, adminPhases } from "../lib/admin-navigation";
import { includesPlayoffStep } from "../lib/open-playoff-review";

const FLOW_STEPS = [
  ["overview", "Översikt"],
  ["cupinfo", "Cupinfo"],
  ["teams", "Lag"],
  ["groups", "Grupper"],
  ["venues", "Planer & tider"],
  ["rules", "Regler"],
  ["schedule", "Schema"],
  ["playoffs", "Slutspel"],
  ["publish", "Kontroll & publicering"],
] as const;

const TOOL_STEPS = [
  ["referees", "Domare"],
  ["reporting", "Matchrapportering"],
  ["import", "Uppdatera från fil"],
  ["export", "PDF & export"],
] as const;

const STEP_GUIDE:Record<string,{goal:string;action:string;done:string}> = {
  overview:{goal:"Se vad som redan är klart och var du bör börja.",action:"Öppna det rekommenderade nästa steget på översikten.",done:"Du vet vilken uppgift som står på tur."},
  cupinfo:{goal:"Säkerställ att besökare får rätt grundinformation.",action:"Kontrollera namn, datum, arrangör, plats och kontaktuppgifter. Spara sedan.",done:"Uppgifterna är korrekta och sparade."},
  teams:{goal:"Få in rätt lag och tydliga matchställ.",action:"Kontrollera lagnamn och klass. Sök sedan matchställ eller klubbmärke.",done:"Alla deltagande lag finns med och deras ställ är granskade."},
  groups:{goal:"Placera varje lag i rätt grupp.",action:"Skapa grupper och välj grupp för alla lag som ska spela gruppspel.",done:"Inget lag som ska gruppspela är ogrupperat."},
  venues:{goal:"Beskriv cupens verkliga plankapacitet.",action:"Lägg in planer, öppettider och eventuella begränsningar.",done:"Varje spelbar plan har korrekta tider."},
  rules:{goal:"Bestäm reglerna som schemat ska följa.",action:"Kontrollera matchtid, pauser, minsta vila och tabellregler.",done:"Reglerna motsvarar cupens upplägg."},
  schedule:{goal:"Skapa ett genomförbart matchprogram.",action:"Granska redan importerade matcher. Saknas matcher kan du återställa dem från första importen eller skapa ett förslag.",done:"Alla matcher har tid, plan och tillräcklig vila."},
  referees:{goal:"Gör domarbemanningen tydlig.",action:"Lägg till domare eller välj att hantera bemanningen senare.",done:"Varje match har en plan för domare."},
  playoffs:{goal:"Koppla slutspelet till gruppresultaten.",action:"Kontrollera kvalvägar, slutspelsmatcher och tider.",done:"Varje slutspelsplats går att härleda korrekt."},
  publish:{goal:"Släpp bara en cup som besökare kan lita på.",action:"Åtgärda blockerare, förhandsgranska publikvyn och publicera.",done:"Cupen är publicerad och publikvyn är kontrollerad."},
  reporting:{goal:"Förbered snabb rapportering under cupdagen.",action:"Kontrollera rapportörsåtkomst och hur resultat ska registreras.",done:"Rätt personer kan rapportera utan adminåtkomst."},
  import:{goal:"Läs in ändringar utan att förstöra befintligt arbete.",action:"Förhandsgranska filen, kontrollera skillnader och bekräfta först därefter.",done:"Importerade uppgifter är granskade och sparade."},
  export:{goal:"Ta ut material för funktionärer och reservrutiner.",action:"Välj PDF eller export och kontrollera innehållet före utskrift.",done:"Rätt underlag är hämtat och går att använda."},
};

type StepId = (typeof FLOW_STEPS)[number][0] | (typeof TOOL_STEPS)[number][0];
const IDS = new Set<string>([...FLOW_STEPS,...TOOL_STEPS].map(([id]) => id));

function stepFromHash(): StepId {
  if (typeof window === "undefined") return "overview";
  const value = window.location.hash.replace(/^#/, "");
  return IDS.has(value) ? value as StepId : "overview";
}

function announceStep(step:StepId) {
  document.documentElement.dataset.adminStep = step;
  window.dispatchEvent(new CustomEvent("cupnavi:admin-step", { detail: step }));
}

export default function AdminStepFlow() {
  const [step, setStep] = useState<StepId>("overview");
  const [arrangementType,setArrangementType]=useState("tournament");
  const [cupPublished,setCupPublished]=useState(false);

  const select = useCallback((next: StepId) => {
    setStep(next);
    announceStep(next);
    const url = new URL(window.location.href);
    url.hash = next;
    window.history.pushState({}, "", `${url.pathname}${url.search}${url.hash}`);
    window.scrollTo({ top: 0, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" });
  }, []);

  useEffect(() => {
    const sync = () => {
      const next = stepFromHash();
      setStep(next);
      announceStep(next);
    };
    sync();
    window.addEventListener("hashchange", sync);
    window.addEventListener("popstate", sync);
    return () => {
      window.removeEventListener("hashchange", sync);
      window.removeEventListener("popstate", sync);
      delete document.documentElement.dataset.adminStep;
    };
  }, []);

  useEffect(()=>{
    const sync=(event?:Event)=>setArrangementType((event as CustomEvent<string>|undefined)?.detail || document.documentElement.dataset.arrangementType || "tournament");
    sync();
    window.addEventListener("cupnavi:arrangement-type",sync);
    return()=>window.removeEventListener("cupnavi:arrangement-type",sync);
  },[]);

  useEffect(()=>{
    const sync=(event:Event)=>setCupPublished(Boolean((event as CustomEvent<boolean>).detail));
    window.addEventListener("cupnavi:admin-cup-publication",sync);
    return()=>window.removeEventListener("cupnavi:admin-cup-publication",sync);
  },[]);

  const activeFlow=useMemo(()=>FLOW_STEPS.filter(([id])=>{
    if(id==="playoffs")return includesPlayoffStep(arrangementType,step);
    return id!=="groups"||arrangementType!=="matchcamp";
  }),[arrangementType,step]);

  const index = useMemo(() => activeFlow.findIndex(([id]) => id === step), [activeFlow,step]);
  const tool = TOOL_STEPS.find(([id])=>id===step);
  const previous = index > 0 ? activeFlow[index - 1] : null;
  const next = index >= 0 && index < activeFlow.length - 1 ? activeFlow[index + 1] : null;
  const guide = STEP_GUIDE[step] || STEP_GUIDE.overview;

  useEffect(()=>{
    if(index<0&&!tool)select("overview");
  },[index,select,tool]);

  return <section className="cn-step-guide" aria-label="Cupens arbetsflöde">
    <nav className="cn-phases" aria-label="Arbetsfaser">{adminPhases.map(phase=><button key={phase.id} type="button" aria-current={adminPhase(step)===phase.id?"step":undefined} onClick={()=>select(phase.step)}>{phase.label}</button>)}</nav>
    <div className="cn-step-guide__body"><div><strong>{tool?.[1] || activeFlow[index]?.[1] || "Översikt"}</strong><p>{cupPublished&&step==="overview"?"Cupen är publicerad. Följ matcherna och rapportera resultat under cupdagen.":guide.action}</p></div>
    <div className="cn-step-guide__actions">{tool?<button type="button" onClick={()=>select("overview")}>Till översikten</button>:cupPublished&&step==="overview"?<button className="cn-primary" type="button" onClick={()=>select("reporting")}>Öppna rapportering →</button>:<>{previous&&<button type="button" onClick={()=>select(previous[0])}>Föregående</button>}{next&&<button className="cn-primary" type="button" onClick={()=>select(next[0])}>Nästa: {next[1]} →</button>}</>}</div></div>
    {!(cupPublished&&step==="overview")&&<details><summary>Vad behöver vara klart?</summary><p>{guide.done}</p></details>}
  </section>;
}
