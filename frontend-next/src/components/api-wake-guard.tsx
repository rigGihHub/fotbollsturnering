"use client";

import { useEffect, useRef, useState } from "react";
import { CLIENT_API_BASE } from "../lib/client-api";

type WakeState = "checking" | "waking" | "online" | "failed";

const POLL_MS = 3000;
const REQUEST_TIMEOUT_MS = 7000;
const MAX_WAIT_MS = 75000;

async function healthCheck() {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(`${CLIENT_API_BASE}/health`, {
      cache: "no-store",
      signal: controller.signal,
    });
    return response.ok;
  } catch {
    return false;
  } finally {
    window.clearTimeout(timeout);
  }
}

export default function ApiWakeGuard() {
  const [state, setState] = useState<WakeState>("checking");
  const startedAt = useRef(0);
  const running = useRef(false);

  useEffect(() => {
    let cancelled = false;
    let pollTimer: number | undefined;

    async function poll() {
      if (cancelled || running.current) return;
      running.current = true;
      const ok = await healthCheck();
      running.current = false;
      if (cancelled) return;

      if (ok) {
        setState("online");
        return;
      }

      const elapsed = Date.now() - startedAt.current;
      if (elapsed >= MAX_WAIT_MS) {
        setState("failed");
        return;
      }
      setState("waking");
      pollTimer = window.setTimeout(poll, POLL_MS);
    }

    startedAt.current = Date.now();
    void poll();

    return () => {
      cancelled = true;
      running.current = false;
      if (pollTimer) window.clearTimeout(pollTimer);
    };
  }, []);

  // A routine cold start is infrastructure detail, not useful visitor
  // information. Individual pages own their loading state and can keep their
  // normal CupNavi shell visible while the API becomes available.
  if (state === "online" || state === "checking" || state === "waking") return null;

  const failed = state === "failed";
  return (
    <div
      role={failed ? "alert" : "status"}
      aria-live="polite"
      style={{
        position: "sticky",
        top: 0,
        zIndex: 100,
        margin: "0 auto 12px",
        maxWidth: 1120,
        padding: "12px 16px",
        border: "2px solid #17323e",
        borderTop: 0,
        borderRadius: "0 0 14px 14px",
        background: failed ? "#f9e7e3" : "#fff3bd",
        color: "#102630",
        boxShadow: "0 5px 18px rgba(16,38,48,.12)",
        fontWeight: 750,
      }}
    >
      <div style={{display:"flex",gap:12,alignItems:"center",justifyContent:"space-between",flexWrap:"wrap"}}>
        <div>
          <strong style={{display:"block",marginBottom:2}}>CupNavi kunde inte ansluta</strong>
          <span style={{fontSize:13,fontWeight:600}}>
            Försök igen. Du behöver inte logga ut och inga sparade uppgifter påverkas.
          </span>
        </div>
        {failed && (
          <button
            type="button"
            onClick={() => window.location.reload()}
            style={{minHeight:40,padding:"8px 12px",border:"1.5px solid #17323e",borderRadius:9,background:"#102630",color:"white",fontWeight:850,cursor:"pointer"}}
          >
            Försök igen
          </button>
        )}
      </div>
    </div>
  );
}
