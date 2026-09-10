const STREAMLIT_ADMIN = "https://cupnavi.streamlit.app/";

const adminModules = [
  { n: "01", title: "Cupöversikt", text: "Cupnamn, datum, anläggningar och publiceringsstatus." },
  { n: "02", title: "Lag & grupper", text: "Lag, klasser, grupper, tröjfärger och import." },
  { n: "03", title: "Schema", text: "Planer, tider, domare, viloregler och manuella justeringar." },
  { n: "04", title: "Slutspel", text: "A/B-slutspel, bronsmatch och kvalificeringsregler." },
  { n: "05", title: "Roller & koder", text: "Domare, matchrapportörer och lagledarkoder samlade på ett ställe." },
  { n: "06", title: "Publicera", text: "Förhandsgranskning, checklista och publicering till publikvyn." },
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
            <h1>Admin. På väg hem.</h1>
            <p className="admin-hero__lead">
              Den publika CupNavi-vyn kör nu i Next.js. Administrationsdelen flyttas stegvis hit utan att störa den fungerande cupdriften.
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
          <span className="admin-now__eyebrow">ADMIN JUST NU</span>
          <h2>Fortsätt administrera i Streamlit</h2>
          <p>Inga adminfunktioner har stängts av. Den gamla adminsidan är fortfarande den aktiva kontrollpanelen tills motsvarande Next.js-flöden är klara.</p>
        </div>
        <a className="admin-primary-cta" href={STREAMLIT_ADMIN} target="_blank" rel="noreferrer">
          Öppna CupNavi Admin <span>↗</span>
        </a>
      </section>

      <section className="admin-module-section">
        <div className="section-heading section-heading--compact">
          <span>CN//CONTROL</span>
          <h2>Nya adminytan</h2>
          <p>Det här är strukturen som flyttas in härnäst.</p>
        </div>
        <div className="admin-module-grid">
          {adminModules.map((item) => (
            <article className="admin-module" key={item.n}>
              <div className="admin-module__meta"><span>{item.n}</span><span>PLANERAD</span></div>
              <h3>{item.title}</h3>
              <p>{item.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="admin-migration-note">
        <span>CN//MIGRATION RULE</span>
        <strong>Ingen big-bang-migrering.</strong>
        <p>Varje adminmodul flyttas först när den har funktionell parity, testad dataskrivning och säker behörighetskontroll. Streamlit ligger kvar som fallback under övergången.</p>
      </section>
    </main>
  );
}
