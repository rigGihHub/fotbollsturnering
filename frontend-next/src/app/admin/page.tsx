const PUBLIC_CUP = "/cup/slottskampen-2026";

const nav = ["Översikt", "Cupinfo", "Lag", "Grupper", "Planer & tider", "Regler", "Schema", "Domare", "Slutspel", "Publicering", "Matchrapportering", "Import", "PDF & export"];

const checks = [
  ["Cupinfo", "Påbörjad"],
  ["Lag", "Ej klar"],
  ["Grupper", "Ej klar"],
  ["Schema", "Ej klar"],
  ["Publicering", "Ej klar"],
];

export default function AdminPage() {
  return (
    <main className="admin-workspace">
      <aside className="admin-sidebar">
        <div className="admin-sidebar__cup"><span>AKTIV CUP</span><strong>Slottskampen 2026</strong><small>24 oktober 2026</small></div>
        <nav aria-label="Cupadministration">
          {nav.map((item, index) => <a className={index === 0 ? "is-active" : ""} href={index === 1 ? "#cupinfo" : "#"} key={item}><span>{String(index + 1).padStart(2,"0")}</span>{item}</a>)}
        </nav>
        <a className="admin-public-link" href={PUBLIC_CUP}>Visa publik cup ↗</a>
      </aside>

      <section className="admin-main">
        <header className="admin-pagehead">
          <div><p className="kicker">CN//ADMIN</p><h1>Cupöversikt</h1><p>Allt som krävs för att få Slottskampen redo för matchdag.</p></div>
          <div className="admin-pagehead__actions"><span className="admin-draft">UTKAST</span><a href={PUBLIC_CUP}>Förhandsgranska</a></div>
        </header>

        <section className="admin-dashboard-grid">
          <article className="admin-panel admin-panel--status">
            <div className="admin-panel__top"><span>PUBLICERINGSSTATUS</span><strong>2 / 5</strong></div>
            <h2>Inte redo att publicera än</h2>
            <div className="admin-checks">{checks.map(([name,status],i)=><div key={name}><span className={i===0?"is-progress":""}>{i===0?"◐":"○"}</span><strong>{name}</strong><small>{status}</small></div>)}</div>
          </article>
          <article className="admin-panel admin-panel--codes">
            <div className="admin-panel__top"><span>ROLLER & KODER</span><strong>ALLTID NÄRA</strong></div>
            <h2>Åtkomst</h2>
            <p>Koder visas här när den autentiserade kodtjänsten är inkopplad. Vi visar aldrig påhittade koder.</p>
            <div className="admin-code-placeholder">Admin <b>••••••</b></div>
            <div className="admin-code-placeholder">Domare <b>••••••</b></div>
            <div className="admin-code-placeholder">Matchrapportör <b>••••••</b></div>
          </article>
        </section>

        <section className="admin-panel admin-cupinfo" id="cupinfo">
          <div className="admin-panel__top"><span>01 / CUPINFO</span><strong>NÄSTA FUNKTION</strong></div>
          <div className="admin-cupinfo__head"><div><h2>Grunduppgifter</h2><p>Det här blir första skrivande Next-modulen. Fälten låses tills admin-API och behörighet är inkopplade.</p></div><span className="admin-lock">API KRÄVS</span></div>
          <div className="admin-form-grid">
            <label>Cupnamn<input value="Slottskampen 2026" readOnly /></label>
            <label>Datum<input value="24 oktober 2026" readOnly /></label>
            <label>Anläggning<input value="" placeholder="Hämtas från CupNavi-data" readOnly /></label>
            <label>Kontakt<input value="" placeholder="Hämtas från CupNavi-data" readOnly /></label>
          </div>
          <div className="admin-form-footer"><span>Inga ändringar sparas från den här sidan ännu.</span><button disabled>Spara Cupinfo</button></div>
        </section>
      </section>
    </main>
  );
}
