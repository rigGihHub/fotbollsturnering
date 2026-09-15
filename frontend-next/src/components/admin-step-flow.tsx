"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

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
  teams:{goal:"Få in rätt lag och tydliga matchställ.",action:"Kontrollera lagnamn och klass. Sök sedan tröjfärger och bekräfta källbelagda förslag.",done:"Alla deltagande lag finns med och deras ställ är granskade."},
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

  const select = useCallback((next: StepId) => {
    setStep(next);
    announceStep(next);
    const url = new URL(window.location.href);
    url.hash = next;
    window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  useEffect(() => {
    const sync = () => {
      const next = stepFromHash();
      setStep(next);
      announceStep(next);
    };
    sync();
    window.addEventListener("hashchange", sync);
    return () => {
      window.removeEventListener("hashchange", sync);
      delete document.documentElement.dataset.adminStep;
    };
  }, []);

  useEffect(()=>{
    const sync=(event?:Event)=>setArrangementType((event as CustomEvent<string>|undefined)?.detail || document.documentElement.dataset.arrangementType || "tournament");
    sync();
    window.addEventListener("cupnavi:arrangement-type",sync);
    return()=>window.removeEventListener("cupnavi:arrangement-type",sync);
  },[]);

  const activeFlow=useMemo(()=>arrangementType==="matchcamp"
    ? FLOW_STEPS.filter(([id])=>id!=="groups"&&id!=="playoffs")
    : arrangementType==="tournament"
      ? FLOW_STEPS.filter(([id])=>id!=="playoffs")
      : FLOW_STEPS,[arrangementType]);

  const index = useMemo(() => activeFlow.findIndex(([id]) => id === step), [activeFlow,step]);
  const tool = TOOL_STEPS.find(([id])=>id===step);
  const previous = index > 0 ? activeFlow[index - 1] : null;
  const next = index >= 0 && index < activeFlow.length - 1 ? activeFlow[index + 1] : null;
  const guide = STEP_GUIDE[step] || STEP_GUIDE.overview;

  useEffect(()=>{
    if(index<0&&!tool)select("overview");
  },[index,select,tool]);

  if(tool) return <section className="admin-step-flow admin-step-flow--tool" aria-label="Cupverktyg">
    <div className="admin-step-flow__meta"><span>VERKTYG & CUPDRIFT</span><strong>{tool[1]}</strong></div>
    <p>{guide.goal} {guide.action}</p>
    <button type="button" onClick={()=>select("overview")}>← Till cupöversikten</button>
  </section>;

  return (
    <section className="admin-step-flow" aria-label="Cupens arbetsflöde">
      <div className="admin-step-flow__meta">
        <span>{index===0?(arrangementType==="matchcamp"?"DIN MATCHCAMPGUIDE":"DIN CUPGUIDE"):`STEG ${index} AV ${activeFlow.length-1}`}</span>
        <strong>{activeFlow[index]?.[1] || "Översikt"}</strong>
      </div>
      <div className="admin-step-flow__track" aria-hidden="true"><span style={{width:`${index===0?0:(index / (activeFlow.length-1)) * 100}%`}} /></div>
      <div className="admin-step-flow__guide">
        <div><span>MÅL</span><strong>{guide.goal}</strong></div>
        <div><span>GÖR NU</span><strong>{guide.action}</strong></div>
        <div><span>KLAR NÄR</span><strong>{guide.done}</strong></div>
      </div>
      <div className="admin-step-flow__actions">
        <button type="button" disabled={!previous} onClick={() => previous && select(previous[0])}>← Föregående</button>
        <button type="button" className="is-primary" disabled={!next} onClick={() => next && select(next[0])}>{next ? `Nästa: ${next[1]} →` : "Flödet klart"}</button>
      </div>
    </section>
  );
}
