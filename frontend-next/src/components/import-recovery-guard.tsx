"use client";

import { useEffect, useState } from "react";

const CUP_KEY = "cupnavi_admin_active_cup_v651";

type RecoveryState = {
  cupId: string;
  currentCupId: string | null;
};

function readRecoveryState(ignoredCupId:string|null): RecoveryState | null {
  const cupId = localStorage.getItem(CUP_KEY);
  if (!cupId || cupId === ignoredCupId) return null;
  const currentCupId = new URL(window.location.href).searchParams.get("cup");
  if (currentCupId === cupId) return null;
  return { cupId, currentCupId };
}

export default function ImportRecoveryGuard() {
  const [recovery, setRecovery] = useState<RecoveryState | null>(null);
  const [ignoredCupId, setIgnoredCupId] = useState<string|null>(null);

  useEffect(() => {
    const sync = () => setRecovery(readRecoveryState(ignoredCupId));
    sync();
    window.addEventListener("storage", sync);
    window.addEventListener("focus", sync);
    window.addEventListener("popstate", sync);
    window.addEventListener("cupnavi:admin-step", sync);
    return () => {
      window.removeEventListener("storage", sync);
      window.removeEventListener("focus", sync);
      window.removeEventListener("popstate", sync);
      window.removeEventListener("cupnavi:admin-step", sync);
    };
  }, [ignoredCupId]);

  if (!recovery) return null;

  function openDraft() {
    const url = new URL(window.location.href);
    url.searchParams.set("cup", recovery!.cupId);
    url.hash = "overview";
    window.location.assign(`${url.pathname}${url.search}${url.hash}`);
  }

  function dismiss() {
    setIgnoredCupId(recovery!.cupId);
    setRecovery(null);
  }

  return (
    <aside
      role="status"
      aria-live="polite"
      style={{position:"fixed",zIndex:1300,left:"max(10px, env(safe-area-inset-left))",right:"max(10px, env(safe-area-inset-right))",bottom:"max(10px, env(safe-area-inset-bottom))",margin:"0 auto",maxWidth:760,display:"grid",gridTemplateColumns:"44px minmax(0,1fr) auto 36px",alignItems:"center",gap:10,padding:"11px 12px",border:"1.5px solid #9b6b21",borderRadius:14,background:"#fff8df",color:"#3f2b10",boxShadow:"0 10px 30px rgba(10,24,31,.24)"}}
    >
      <div aria-hidden="true" style={{width:40,height:40,borderRadius:999,display:"grid",placeItems:"center",border:"1.5px solid currentColor",fontSize:22,fontWeight:900}}>↻</div>
      <div style={{display:"grid",gap:3,minWidth:0}}>
        <strong style={{fontSize:14}}>Det finns ett aktivt cup-utkast</strong>
        <span style={{fontSize:12,lineHeight:1.35}}>Om en import avbröts kan delar redan vara sparade. Öppna utkastet och kontrollera vad som hann skapas i stället för att börja om.</span>
      </div>
      <button type="button" onClick={openDraft} style={{minHeight:42,padding:"9px 13px",border:"1.5px solid #3f2b10",borderRadius:9,background:"#3f2b10",color:"#fff",fontWeight:900,cursor:"pointer",whiteSpace:"nowrap"}}>Öppna utkastet</button>
      <button type="button" onClick={dismiss} aria-label="Dölj" style={{width:34,height:34,border:"1px solid rgba(63,43,16,.35)",borderRadius:8,background:"transparent",color:"inherit",fontSize:20,cursor:"pointer"}}>×</button>
    </aside>
  );
}
