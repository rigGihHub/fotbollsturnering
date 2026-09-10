const PUBLIC_CUP = "/cup/slottskampen-2026";

const nav = [
  ["Översikt", "#overview"], ["Cupinfo", "#cupinfo"], ["Lag", "#teams"], ["Grupper", "#groups"],
  ["Planer & tider", "#venues"], ["Regler", "#rules"], ["Schema", "#schedule"], ["Domare", "#referees"],
  ["Slutspel", "#playoffs"], ["Publicering", "#publish"], ["Matchrapportering", "#reporting"], ["Import", "#import"], ["PDF & export", "#export"]
];

const checks = [["Cupinfo", "Påbörjad"], ["Lag", "Ej klar"], ["Grupper", "Ej klar"], ["Schema", "Ej klar"], ["Publicering", "Ej klar"]];

const modules = [
  ["teams","03","Lag","Lägg till lag, klasser, tröjfärger och laguppställningar."],
  ["groups","04","Grupper","Fördela lag i grupper och kontrollera gruppstorlekar."],
  ["venues","05","Planer & tider","Anläggningar, planer, matchlängd, pauser och tillgängliga tider."],
  ["rules","06","Regler","Poängregler, vilotid, färgkrockar och turneringsinställningar."],
  ["schedule","07","Schema","Generera dynamiskt schema eller justera ett importerat schema manuellt."],
  ["referees","08","Domare","Lägg in domare nu eller tillsätt dem senare."],
  ["playoffs","09","Slutspel","A/B-slutspel, valbara kvalificerade placeringar, bronsmatch och final."],
  ["publish","10","Publicering","Förhandsgranska cupen och publicera först när checklistan är klar."],
  ["reporting","11","Matchrapportering","Resultat, målskyttar, assist och kort när statistiken är aktiverad."],
  ["import","12","Import","Läs in tidigare cupprogram från dokument eller flera bilder utan att skriva över data tyst."],
  ["export","13","PDF & export","Förhandsgranska, skapa och ladda ned cupens PDF från samma flöde."]
];

export default function AdminPage() {
  return (
    <main className="admin-workspace">
      <aside className="admin-sidebar">
        <div className="admin-sidebar__cup"><span>AKTIV CUP</span><strong>Slottskampen 2026</strong><small>24 oktober 2026</small></div>
        <nav aria-label="Cupadministration">{nav.map(([item,href], index) => <a className={index === 0 ? "is-active" : ""} href={href} key={item}><span>{String(index + 1).padStart(2,"0")}</span>{item}</a>)}</nav>
        <a className="admin-public-link" href={PUBLIC_CUP}>Visa publik cup ↗</a>
      </aside>

      <section className="admin-main" id="overview">
        <header className="admin-pagehead"><div><p className="kicker">CN//ADMIN</p><h1>Cupöversikt</h1><p>Allt som krävs för att få Slottskampen redo för matchdag.</p></div><div className="admin-pagehead__actions"><span className="admin-draft">UTKAST</span><a href={PUBLIC_CUP}>Förhandsgranska</a></div></header>
        <section className="admin-dashboard-grid">
          <article className="admin-panel admin-panel--status"><div className="admin-panel__top"><span>PUBLICERINGSSTATUS</span><strong>1 / 5</strong></div><h2>Inte redo att publicera än</h2><div className="admin-checks">{checks.map(([name,status],i)=><div key={name}><span className={i===0?"is-progress":""}>{i===0?"◐":"○"}</span><strong>{name}</strong><small>{status}</small></div>)}</div></article>
          <article className="admin-panel admin-panel--codes"><div className="admin-panel__top"><span>ROLLER & KODER</span><strong>ALLTID NÄRA</strong></div><h2>Åtkomst</h2><p>Koder visas här när den autentiserade kodtjänsten är inkopplad. Vi visar aldrig påhittade koder.</p><div className="admin-code-placeholder">Admin <b>••••••</b></div><div className="admin-code-placeholder">Domare <b>••••••</b></div><div className="admin-code-placeholder">Matchrapportör <b>••••••</b></div></article>
        </section>

        <section className="admin-panel admin-cupinfo" id="cupinfo"><div className="admin-panel__top"><span>02 / CUPINFO</span><strong>NÄSTA FUNKTION</strong></div><div className="admin-cupinfo__head"><div><h2>Grunduppgifter</h2><p>Första skrivande Next-modulen. Fälten förblir låsta tills riktig behörighet och skriv-API finns.</p></div><span className="admin-lock">API KRÄVS</span></div><div className="admin-form-grid"><label>Cupnamn<input value="Slottskampen 2026" readOnly /></label><label>Datum<input value="24 oktober 2026" readOnly /></label><label>Anläggning<input value="" placeholder="Hämtas från CupNavi-data" readOnly /></label><label>Kontakt<input value="" placeholder="Hämtas från CupNavi-data" readOnly /></label></div><div className="admin-form-footer"><span>Inga ändringar sparas från den här sidan ännu.</span><button disabled>Spara Cupinfo</button></div></section>

        <section className="admin-module-grid" aria-label="Cupens arbetsflöde">{modules.map(([id,n,title,text]) => <article className="admin-panel admin-module-card" id={id} key={id}><div className="admin-panel__top"><span>{n} / MODUL</span><strong>FÖRBEREDD</strong></div><h2>{title}</h2><p>{text}</p><button disabled>Öppna när datalagret är inkopplat</button></article>)}</section>
      </section>
    </main>
  );
}
