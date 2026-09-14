"use client";

import { useEffect, useState } from "react";
import CupCreateLauncherV6 from "./cup-create-launcher-v6";
import { CLIENT_API_BASE } from "../lib/client-api";

const TOKEN_KEY = "cupnavi_admin_session_v629";

type SessionPayload = { account?: { role?: string | null; is_owner?: boolean } };

export default function CupCreateLauncherResilient() {
  const [hasToken, setHasToken] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    function schedule(delay = 750) {
      if (cancelled) return;
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => void verifyOwner(), delay);
    }

    async function verifyOwner() {
      if (cancelled || ready) return;
      const token = localStorage.getItem(TOKEN_KEY);

      // The resilient admin shell may briefly restore the token after a
      // transient API/session failure. Never give up permanently just because
      // the token is absent in one render cycle.
      if (!token) {
        if (!cancelled) setHasToken(false);
        schedule(500);
        return;
      }

      if (!cancelled) setHasToken(true);
      try {
        const response = await fetch(`${CLIENT_API_BASE}/api/admin/session`, {
          headers: { Authorization: `Bearer ${token}` },
          cache: "no-store",
        });

        if (response.ok) {
          const payload = (await response.json()) as SessionPayload;
          const owner = payload.account?.role === "owner" || payload.account?.is_owner === true;
          if (owner) {
            if (!cancelled) setReady(true);
            return;
          }

          // A valid non-owner session should not see owner controls.
          if (!cancelled) {
            setReady(false);
            setHasToken(true);
          }
          return;
        }

        // 401 can occur while another component is recovering the same local
        // session. Keep the launcher alive and verify again instead of hiding
        // it forever.
        schedule(response.status === 401 ? 700 : 1800);
      } catch {
        // Render free instances and mobile networks can be briefly unavailable.
        schedule(1400);
      }
    }

    const onStorage = (event: StorageEvent) => {
      if (event.key === TOKEN_KEY) schedule(50);
    };
    const onFocus = () => schedule(50);
    window.addEventListener("storage", onStorage);
    window.addEventListener("focus", onFocus);

    void verifyOwner();
    return () => {
      cancelled = true;
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("focus", onFocus);
      if (timer) clearTimeout(timer);
    };
  }, [ready]);

  if (ready) return <CupCreateLauncherV6 />;
  if (!hasToken) return null;

  return (
    <div className="cup-create-toolbar cup-create-toolbar--pending" aria-live="polite">
      <div><span>ÄGARKONTO</span><strong>Verifierar behörighet…</strong></div>
      <button type="button" disabled>+ Ny cup</button>
    </div>
  );
}
