"use client";

import { useEffect, useState } from "react";
import { getPublicCups } from "@/lib/api";
import type { PublicCupListing, PublicCupStatus } from "@/lib/types";
import styles from "./PublicCupDirectory.module.css";

const categories: Array<{status: PublicCupStatus; label: string; empty: string}> = [
  {status: "ongoing", label: "Pågående", empty: "Inga publicerade matchcamper eller cuper pågår just nu."},
  {status: "upcoming", label: "Kommande", empty: "Inga kommande matchcamper eller cuper är publicerade ännu."},
  {status: "completed", label: "Avslutade", empty: "Inga avslutade matchcamper eller cuper är publicerade ännu."},
  {status: "undated", label: "Datum saknas", empty: "Inga arrangemang saknar datum."},
];
const dateFormatter = new Intl.DateTimeFormat("sv-SE", {day: "numeric", month: "short", year: "numeric", timeZone: "UTC"});

function dates(cup: PublicCupListing): string {
  if (!cup.start_date) return "Datum ej angivet";
  const start = dateFormatter.format(new Date(`${cup.start_date}T12:00:00Z`));
  return cup.end_date && cup.end_date !== cup.start_date
    ? `${start} – ${dateFormatter.format(new Date(`${cup.end_date}T12:00:00Z`))}` : start;
}

function arrangementLabel(type: string | null): string {
  if (type === "matchcamp") return "Matchcamp";
  if (type === "single_match") return "Match";
  if (type === "custom") return "Arrangemang";
  return "Cup";
}

export default function PublicCupDirectory() {
  const [cups, setCups] = useState<PublicCupListing[]>([]);
  const [selected, setSelected] = useState<PublicCupStatus>("ongoing");
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setFailed(false);
    getPublicCups().then(payload => {
      if (!active) return;
      setCups(payload.cups);
      setSelected(categories.find(category => payload.cups.some(cup => cup.status === category.status))?.status ?? "ongoing");
    }).catch(() => {
      if (active) setFailed(true);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [attempt]);

  const visible = cups.filter(cup => cup.status === selected);
  return (
    <section id="public-cups" className={styles.directory} aria-labelledby="directory-title">
      <div className={styles.heading}>
        <p>HITTA DITT ARRANGEMANG</p>
        <h2 id="directory-title">Följ matchcamper och cuper.</h2>
      </div>
      <p className={styles.intro}>Öppna ett arrangemang för spelschema, tabeller och resultat.</p>
      {loading ? <p className={styles.message} role="status">Hämtar publicerade arrangemang…</p> : failed ? (
        <div className={styles.message}>
          <p role="alert">Det gick inte att hämta arrangemangen. Kontrollera uppkopplingen och försök igen.</p>
          <button className={styles.retry} onClick={() => setAttempt(value => value + 1)}>Försök igen</button>
        </div>
      ) : (
        <>
          <div className={styles.filters} role="group" aria-label="Välj arrangemangens status">
            {categories.filter(category => category.status !== "undated" || cups.some(cup => cup.status === "undated")).map(category => (
              <button key={category.status} aria-pressed={selected === category.status} aria-controls="directory-results" onClick={() => setSelected(category.status)}>
                {category.label} <span>{cups.filter(cup => cup.status === category.status).length}</span>
              </button>
            ))}
          </div>
          <div id="directory-results" aria-live="polite" aria-atomic="true">
            {visible.length ? (
              <ul className={styles.cards}>
                {visible.map(cup => (
                  <li key={cup.id}>
                    <a className={styles.card} href={`/cup/${encodeURIComponent(cup.public_slug || String(cup.id))}`} aria-label={`Öppna ${cup.name}`}>
                      <div className={styles.cardTop}><span>{arrangementLabel(cup.arrangement_type)}</span><span className={styles.badge}>{categories.find(category => category.status === cup.status)?.label}</span></div>
                      <h3>{cup.name}</h3>
                      <p className={styles.date}>{dates(cup)}</p>
                      {cup.arena_address ? <p className={styles.venue}>{cup.arena_address}</p> : null}
                      <span className={styles.open}>Öppna arrangemanget <span aria-hidden="true">→</span></span>
                    </a>
                  </li>
                ))}
              </ul>
            ) : <p className={styles.message}>{categories.find(category => category.status === selected)?.empty}</p>}
          </div>
        </>
      )}
    </section>
  );
}
