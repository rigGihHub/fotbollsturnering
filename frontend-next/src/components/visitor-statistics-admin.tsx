"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { CLIENT_API_BASE } from "../lib/client-api";

type VisitorStatistics = {
  total: number;
  today: number;
  active: number;
  peak: number;
  recorded_since: string | null;
  timezone: "Europe/Stockholm";
  active_window_seconds: 90;
  days: Array<{ date: string; visitors: number; peak: number }>;
};

const numbers = new Intl.NumberFormat("sv-SE");
const dates = new Intl.DateTimeFormat("sv-SE", {
  timeZone: "Europe/Stockholm", day: "numeric", month: "short", year: "numeric",
});
const timestamps = new Intl.DateTimeFormat("sv-SE", {
  timeZone: "Europe/Stockholm", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
});
function dayLabel(value: string): string {
  const date = new Date(value.length === 10 ? `${value}T12:00:00Z` : value);
  return Number.isNaN(date.getTime()) ? value : dates.format(date);
}

export default function VisitorStatisticsAdmin({ token, cupId, cupName }: { token: string; cupId: number; cupName: string }) {
  const [snapshot, setSnapshot] = useState<{ cupId: number; data: VisitorStatistics; period: number; updatedAt: Date } | null>(null);
  const [period, setPeriod] = useState(30);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const request = useRef<AbortController | null>(null);
  const data = snapshot?.cupId === cupId ? snapshot.data : null;
  const updatedAt = snapshot?.cupId === cupId ? snapshot.updatedAt : null;

  const load = useCallback(async () => {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    let timedOut = false;
    const timeout = window.setTimeout(() => { timedOut = true; controller.abort(); }, 10_000);
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${CLIENT_API_BASE}/api/admin/cups/${cupId}/visitors?days=${period}`, {
        headers: { Authorization: `Bearer ${token}` }, cache: "no-store", signal: controller.signal,
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) throw new Error(typeof payload?.detail === "string" ? payload.detail : "Statistiken kunde inte hämtas just nu.");
      if (request.current !== controller || controller.signal.aborted) return;
      if (!payload || !Array.isArray(payload.days)) throw new Error("Statistiken kunde inte läsas. Försök igen.");
      setSnapshot({ cupId, data: payload as VisitorStatistics, period, updatedAt: new Date() });
    } catch (reason) {
      if (request.current !== controller || controller.signal.aborted && !timedOut) return;
      setError(timedOut ? "Det tar för lång tid att hämta statistiken. Försök igen." : reason instanceof Error ? reason.message : "Statistiken kunde inte hämtas just nu.");
    } finally {
      window.clearTimeout(timeout);
      if (request.current === controller) setBusy(false);
    }
  }, [token, cupId, period]);

  useEffect(() => {
    void load();
    return () => { request.current?.abort(); request.current = null; };
  }, [load]);

  const trend = data ? data.days.slice(0, 30).reverse() : [];
  const maximum = Math.max(1, ...trend.map(day => day.visitors));

  return <section className="admin-panel cn-visitor-statistics" id="analytics" aria-labelledby="visitor-statistics-title">
    <div className="cn-visitor-statistics__heading">
      <div><h2 id="visitor-statistics-title">Besöksstatistik</h2><p>{cupName}</p></div>
      <div className="cn-visitor-statistics__controls"><label>Visa dagar<select value={period} disabled={busy} onChange={event => setPeriod(Number(event.target.value))}><option value={30}>Senaste 30 dagarna</option><option value={90}>Senaste 90 dagarna</option><option value={3660}>Alla dagar</option></select></label><button type="button" className="cn-visitor-statistics__refresh" disabled={busy} onClick={() => void load()}>{busy ? "Hämtar…" : error ? "Försök igen" : "Uppdatera statistik"}</button></div>
    </div>
    <p>En besökare är en anonym webbläsare. Samma person kan räknas flera gånger om den använder flera enheter eller webbläsare. Adminförhandsgranskningar räknas inte.</p>
    {error && <div className="cn-visitor-statistics__error" role="alert"><strong>Statistiken kunde inte uppdateras</strong><p>{error}</p>{data && <p>Den senast hämtade statistiken visas fortfarande nedan.</p>}</div>}
    {busy && !data && <p role="status">Hämtar cupens besöksstatistik…</p>}
    {data && <>
      <dl className="cn-visitor-statistics__metrics">
        <div><dt>Besökare idag</dt><dd className="cn-visitor-statistics__metric-value">{numbers.format(data.today)}</dd><dd className="cn-visitor-statistics__metric-help">Unika webbläsare idag</dd></div>
        <div><dt>Besökare totalt</dt><dd className="cn-visitor-statistics__metric-value">{numbers.format(data.total)}</dd><dd className="cn-visitor-statistics__metric-help">Unika webbläsare sedan mätningen började</dd></div>
        <div><dt>Rekord samtidigt</dt><dd className="cn-visitor-statistics__metric-value">{numbers.format(data.peak)}</dd><dd className="cn-visitor-statistics__metric-help">Flest aktiva webbläsare samtidigt</dd></div>
      </dl>
      <p className="cn-visitor-statistics__help">Samma webbläsare kan förekomma flera dagar men räknas bara en gång i totalen. Aktiv betyder att den publika cupvyn har varit öppen och skickat en signal under de senaste {data.active_window_seconds} sekunderna.</p>
      <div className="cn-visitor-statistics__measurement">
        <p>{data.recorded_since ? <>Mätningen började <strong>{dayLabel(data.recorded_since)}</strong>.</> : "Mätningen börjar när någon öppnar den publika cupvyn."}</p>
        {updatedAt && <p>Senast hämtat {timestamps.format(updatedAt)} · {numbers.format(data.active)} aktiva webbläsare då.</p>}
      </div>
      <h3>Besökare per dag</h3>
      <p>{snapshot?.period === 3660 ? "Alla uppmätta dagar visas." : `Visar uppmätta dagar inom de senaste ${snapshot?.period} dagarna.`} Totalt och rekord avser hela mätperioden. Datum och klockslag följer svensk tid.</p>
      {data.days.length > 0 ? <>
        <figure className="cn-visitor-statistics__trend" aria-label={`Dagtrend för de senaste ${trend.length} visade dagarna. Exakta antal och datum finns i tabellen nedanför.`}>
          <div className="cn-visitor-statistics__bars" aria-hidden="true">{trend.map(day => <div key={day.date} title={`${dayLabel(day.date)}: ${numbers.format(day.visitors)} besökare`}><span style={{ height: `${day.visitors / maximum * 100}%` }} /></div>)}</div>
          <figcaption><span>{dayLabel(trend[0].date)} – {dayLabel(trend[trend.length - 1].date)}</span><span>Dagtrend · {trend.length} dagar</span></figcaption>
        </figure>
        <div className="cn-visitor-statistics__table-wrap">
          <table><caption>Besökare och högsta samtidiga antal per dag, senaste dagen först</caption><thead><tr><th scope="col">Datum</th><th scope="col">Besökare</th><th scope="col">Rekord samtidigt</th></tr></thead><tbody>{data.days.map(day => <tr key={day.date}><th scope="row"><time dateTime={day.date}>{dayLabel(day.date)}</time></th><td>{numbers.format(day.visitors)}</td><td>{numbers.format(day.peak)}</td></tr>)}</tbody></table>
        </div>
      </> : <div className="cn-visitor-statistics__empty"><strong>Inga besök registrerade ännu</strong><p>Dagstatistiken visas när någon öppnar cupens publika turneringsvy.</p></div>}
    </>}
  </section>;
}
