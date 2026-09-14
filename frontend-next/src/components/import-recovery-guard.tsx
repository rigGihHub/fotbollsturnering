"use client";

import { useEffect, useState } from "react";

const CUP_KEY = "cupnavi_admin_active_cup_v651";

type RecoveryState = {
  cupId: string;
  currentCupId: string | null;
};

function readRecoveryState(): RecoveryState | null {
  const cupId = localStorage.getItem(CUP_KEY);
  if (!cupId) return null;
  const currentCupId = new URL(window.location.href).searchParams.get("cup");
  if (currentCupId === cupId) return null;
  return { cupId, currentCupId };
}

export default function ImportRecoveryGuard() {
  const [recovery, setRecovery] = useState<RecoveryState | null>(null);

  useEffect(() => {
    const sync = () => setRecovery(readRecoveryState());
    sync();
    const timer = window.setInterval(sync, 750);
    window.addEventListener("storage", sync);
    window.addEventListener("focus", sync);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("storage", sync);
      window.removeEventListener("focus", sync);
    };
  }, []);

  if (!recovery) return null;

  function openDraft() {
    const url = new URL(window.location.href);
    url.searchParams.set("cup", recovery!.cupId);
    url.hash = "overview";
    window.location.assign(`${url.pathname}${url.search}${url.hash}`);
  }

  function dismiss() {
    setRecovery(null);
  }

  return (
    <aside className="cup-import-recovery" role="status" aria-live="polite">
      <div className="cup-import-recovery__icon" aria-hidden="true">↻</div>
      <div className="cup-import-recovery__copy">
        <strong>Det finns ett aktivt cup-utkast</strong>
        <span>Om en import avbröts kan delar redan vara sparade. Öppna utkastet och kontrollera vad som hann skapas i stället för att börja om.</span>
      </div>
      <button type="button" className="cup-import-recovery__open" onClick={openDraft}>Öppna utkastet</button>
      <button type="button" className="cup-import-recovery__dismiss" onClick={dismiss} aria-label="Dölj">×</button>
    </aside>
  );
}
