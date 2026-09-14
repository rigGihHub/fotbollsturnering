"use client";

import { useEffect, useState } from "react";
import CupCreateLauncherV6 from "./cup-create-launcher-v6";
import { CLIENT_API_BASE } from "../lib/client-api";

const TOKEN_KEY = "cupnavi_admin_session_v629";

type SessionPayload = { account?: { role?: string | null; is_owner?: boolean } };

export default function CupCreateLauncherResilient() {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    async function verifyOwner() {
      const token = localStorage.getItem(TOKEN_KEY);
      if (!token || cancelled) return;
      try {
        const response = await fetch(`${CLIENT_API_BASE}/api/admin/session`, {
          headers: { Authorization: `Bearer ${token}` },
          cache: "no-store",
        });
        if (response.ok) {
          const payload = (await response.json()) as SessionPayload;
          if (payload.account?.role === "owner" || payload.account?.is_owner === true) {
            if (!cancelled) setReady(true);
            return;
          }
        }
      } catch {
        // Render free instances can be asleep on first load. Retry below.
      }
      if (!cancelled) timer = setTimeout(verifyOwner, 2000);
    }

    void verifyOwner();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, []);

  return ready ? <CupCreateLauncherV6 /> : null;
}
