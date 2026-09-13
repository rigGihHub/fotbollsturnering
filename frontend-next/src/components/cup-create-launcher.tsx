"use client";

import { FormEvent, useEffect, useState } from "react";
import { CLIENT_API_BASE } from "../lib/client-api";

const API_BASE = CLIENT_API_BASE;
const TOKEN_KEY = "cupnavi_admin_session_v629";
const CUP_KEY = "cupnavi_admin_active_cup_v651";

type SessionPayload = {
  account?: { role?: string | null; is_owner?: boolean };
};

type CreatedCup = {
  id: number;
  name: string;
  public_slug?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  is_published?: number | boolean;
  role?: string;
};

async function request<T>(path: string, options: RequestInit, token: string): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (options.body) headers.set("Content-Type", "application/json");
  headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers, cache: "no-store" });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload && typeof payload.detail === "string" ? payload.detail : `API-fel ${response.status}`;
    throw new Error(detail);
  }
  return payload as T;
}

export default function CupCreateLauncher() {
  const [token, setToken] = useState<string | null>(null);
  const [isOwner, setIsOwner] = useState(false);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) return;
    request<SessionPayload>("/api/admin/session", {}, stored)
      .then(data => {
        const owner = data.account?.role === "owner" || data.account?.is_owner === true;
        if (owner) {
          setToken(stored);
          setIsOwner(true);
        }
      })
      .catch(() => undefined);
  }, []);

  function closeDialog() {
    if (busy) return;
    setOpen(false);
    setError("");
  }

  async function createCup(event: FormEvent) {
    event.preventDefault();
    if (!token || !name.trim()) return;
    if (startDate && endDate && endDate < startDate) {
      setError("Slutdatum kan inte vara före startdatum.");
      return;
    }

    setBusy(true);
    setError("");
    try {
      const cup = await request<CreatedCup>("/api/admin/cups", {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          start_date: startDate || null,
          end_date: endDate || null,
        }),
      }, token);

      localStorage.setItem(CUP_KEY, String(cup.id));
      const url = new URL(window.location.href);
      url.searchParams.set("cup", String(cup.id));
      url.hash = "overview";
      window.location.assign(`${url.pathname}${url.search}${url.hash}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cupen kunde inte skapas.");
      setBusy(false);
    }
  }

  if (!isOwner) return null;

  return <>
    <section className="cup-create-toolbar" aria-label="Cupåtgärder">
      <div>
        <span>CUPADMINISTRATION</span>
        <strong>Skapa och växla mellan cuper</strong>
      </div>
      <button type="button" onClick={() => setOpen(true)}>+ Ny cup</button>
    </section>

    {open && <div className="cup-create-backdrop" role="presentation" onMouseDown={event => {
      if (event.target === event.currentTarget) closeDialog();
    }}>
      <section className="cup-create-dialog" role="dialog" aria-modal="true" aria-labelledby="cup-create-title">
        <div className="cup-create-dialog__head">
          <div>
            <span>NY CUP</span>
            <h2 id="cup-create-title">Starta en ny cup</h2>
          </div>
          <button type="button" className="cup-create-close" onClick={closeDialog} aria-label="Stäng">×</button>
        </div>
        <p className="cup-create-lead">Cupen skapas som utkast och blir inte publik förrän du själv publicerar den.</p>
        <form onSubmit={createCup}>
          <label>
            Cupnamn
            <input autoFocus value={name} onChange={event => setName(event.target.value)} placeholder="Exempel: Höstcupen 2026" maxLength={120} required />
          </label>
          <div className="cup-create-dates">
            <label>
              Startdatum
              <input type="date" value={startDate} onChange={event => {
                const value = event.target.value;
                setStartDate(value);
                if (!endDate) setEndDate(value);
              }} />
            </label>
            <label>
              Slutdatum
              <input type="date" min={startDate || undefined} value={endDate} onChange={event => setEndDate(event.target.value)} />
            </label>
          </div>
          {error && <p className="cup-create-error" role="alert">{error}</p>}
          <div className="cup-create-actions">
            <button type="button" className="is-secondary" onClick={closeDialog} disabled={busy}>Avbryt</button>
            <button type="submit" disabled={busy || !name.trim()}>{busy ? "Skapar…" : "Skapa cup"}</button>
          </div>
        </form>
      </section>
    </div>}
  </>;
}
