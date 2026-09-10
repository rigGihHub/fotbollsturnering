const STREAMLIT_ADMIN = "https://cupnavi.streamlit.app/";
const PUBLIC_CUP = "/cup/slottskampen-2026";

const adminModules = [
  { n: "01", title: "Inloggning & koder", text: "Admin-, domar-, matchrapportör- och lagkoder.", status: "NÄSTA" },
  { n: "02", title: "Cupinfo", text: "Cupnamn, datum, anläggningar, kontakt och publiceringsstatus.", status: "NÄSTA" },
  { n: "03", title: "Lag & grupper", text: "Lag, klasser, grupper, tröjfärger och import.", status: "KÖ" },
  { n: "04", title: "Planer & schema", text: "Planer, tider, viloregler, domare och manuella justeringar.", status: "KÖ" },
  { n: "05", title: "Slutspel & rapportering", text: "A/B-slutspel, brons, resultat, mål, assist och kort.", status: "KÖ" },
  { n: "06", title: "Publicera & export", text: "Checklista, förhandsgranskning, publicering, delning och PDF.", status: "KÖ" },
];

export default function AdminPage() {
  return (
    <main className="page-shell admin-shell">
      <section className="admin-hero">
        <div className="admin-hero__topline">
          <span>CN//ADMIN</span>
          <span>NEXT ADMIN MIGRATION</span>
        </div>
        <div className="admin-hero__content">
          <div>
            <p className="kicker">CupNavi arrangör</p>
            <h1>Admin flyttar in i CupNavi.</h1>
            <p className="admin-hero__lead">
              Vi migrerar administrationen modul för modul. En funktion markeras inte som klar förrän den använder riktig CupNavi-data, kan spara säkert och är testad.
            </p>
          </div>
          <div className="admin-status-card" aria-label="Migreringsstatus">
            <span>STATUS</span>
            <strong>BRIDGE</strong>
            <small>Streamlit → Next</small>
          </div>
        </div>
      </section>

      <section className="admin-now">
        <div>
          <span className="admin-now__eyebrow">DRIFT JUST NU</span>
          <h2>Gamla admin är fortfarande kontrollpanelen</h2>
          <p>Next-admin byggs nu, men vi låtsas inte att funktioner är migrerade innan skrivning, behörighet och tester finns. Använd Streamlit för skarpa ändringar tills respektive modul är klar.</p>
        </div>
        <div style={{display:"flex", gap:"10px", flexWrap:"wrap"}}>
          <a className="admin-primary-cta" href={STREAMLIT_ADMIN} target="_blank" rel="noreferrer">Öppna aktiv Admin <span>↗</span></a>
          <a className="admin-primary-cta" href={PUBLIC_CUP}>Öppna testcup <span>→</span></a>
        </div>
      </section>

      <section className="admin-module-section">
        <div className="section-heading section-heading--compact">
          <span>CN//CONTROL</span>
          <h2>Migreringsordning</h2>
          <p>Först autentisering och Cupinfo. Sedan bygger vi vidare på samma riktiga dataflöde.</p>
        </div>
        <div className="admin-module-grid">
          {adminModules.map((item) => (
            <article className="admin-module" key={item.n}>
              <div className="admin-module__meta"><span>{item.n}</span><span>{item.status}</span></div>
              <h3>{item.title}</h3>
              <p>{item.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="admin-migration-note">
        <span>CN//MIGRATION GATE</span>
        <strong>Riktig funktion före grön etikett.</strong>
        <p>Nästa tekniska leverans är autentiserat admin-API och redigerbar Cupinfo. Streamlit tas inte bort förrän kritisk funktionell parity finns i Next.</p>
      </section>
    </main>
  );
}
