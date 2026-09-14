"use client";

import { useEffect } from "react";
import { CLIENT_API_BASE } from "../lib/client-api";

const TOKEN_KEY = "cupnavi_admin_session_v629";
const CACHE_KEY = "cupnavi_admin_session_payload_v1";

export default function AdminSessionCacheGuard() {
  useEffect(() => {
    const originalFetch = window.fetch.bind(window);

    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
      const method = (init?.method || (input instanceof Request ? input.method : "GET")).toUpperCase();
      const isSessionRead = method === "GET" && url.startsWith(CLIENT_API_BASE) && url.includes("/api/admin/session");

      if (!isSessionRead) return originalFetch(input, init);

      try {
        const response = await originalFetch(input, init);
        if (response.ok) {
          const clone = response.clone();
          clone.text().then(text => {
            try {
              const parsed = JSON.parse(text);
              if (parsed?.account && Array.isArray(parsed?.cups)) sessionStorage.setItem(CACHE_KEY, text);
            } catch {
              // Ignore malformed cache candidates.
            }
          }).catch(() => undefined);
          return response;
        }

        // A real 401 means the server explicitly rejected the session.
        if (response.status === 401) return response;

        const cached = sessionStorage.getItem(CACHE_KEY);
        const token = localStorage.getItem(TOKEN_KEY);
        if (cached && token) {
          return new Response(cached, {
            status: 200,
            headers: { "Content-Type": "application/json", "X-CupNavi-Session": "cached" },
          });
        }
        return response;
      } catch (error) {
        const cached = sessionStorage.getItem(CACHE_KEY);
        const token = localStorage.getItem(TOKEN_KEY);
        if (cached && token) {
          return new Response(cached, {
            status: 200,
            headers: { "Content-Type": "application/json", "X-CupNavi-Session": "cached" },
          });
        }
        throw error;
      }
    };

    return () => {
      window.fetch = originalFetch;
    };
  }, []);

  return null;
}
