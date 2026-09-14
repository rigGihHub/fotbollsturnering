"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

const STEPS = [
  ["overview", "Översikt"],
  ["cupinfo", "Cupinfo"],
  ["teams", "Lag"],
  ["groups", "Grupper"],
  ["venues", "Planer & tider"],
  ["rules", "Regler"],
  ["schedule", "Schema"],
  ["referees", "Domare"],
  ["playoffs", "Slutspel"],
  ["publish", "Publicering"],
  ["reporting", "Matchrapportering"],
  ["import", "Import"],
  ["export", "PDF & export"],
] as const;

type StepId = (typeof STEPS)[number][0];
const IDS = new Set<string>(STEPS.map(([id]) => id));

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

  const index = useMemo(() => STEPS.findIndex(([id]) => id === step), [step]);
  const previous = index > 0 ? STEPS[index - 1] : null;
  const next = index < STEPS.length - 1 ? STEPS[index + 1] : null;

  return (
    <section className="admin-step-flow" aria-label="Cupens arbetsflöde">
      <div className="admin-step-flow__meta">
        <span>STEG {index + 1} AV {STEPS.length}</span>
        <strong>{STEPS[index]?.[1] || "Översikt"}</strong>
      </div>
      <div className="admin-step-flow__track" aria-hidden="true"><span style={{width:`${((index + 1) / STEPS.length) * 100}%`}} /></div>
      <div className="admin-step-flow__actions">
        <button type="button" disabled={!previous} onClick={() => previous && select(previous[0])}>← Föregående</button>
        <button type="button" className="is-primary" disabled={!next} onClick={() => next && select(next[0])}>{next ? `Nästa: ${next[1]} →` : "Flödet klart"}</button>
      </div>
    </section>
  );
}
