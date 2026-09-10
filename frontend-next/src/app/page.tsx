import styles from "./home.module.css";

export default function Home() {
  return (
    <main className="page-shell">
      <div className={styles.home}>
        <section className={styles.hero}>
          <div className={styles.topline}>
            <span>CN//HOME</span>
            <span>FOR TOURNAMENT ORGANIZERS + MATCHDAY PUBLIC</span>
          </div>

          <div className={styles.heroGrid}>
            <div>
              <p className={styles.eyebrow}>CupNavi // Matchday system</p>
              <h1>Hela cupen. Ett ställe.</h1>
              <p className={styles.lead}>
                Skapa cupen, bygg spelschemat, publicera direkt och ge spelare,
                ledare och publik all information de behöver under matchdagen.
              </p>
              <div className={styles.actions}>
                <a className={styles.primary} href="/admin">Skapa eller administrera cup →</a>
                <a className={styles.secondary} href="/cup/slottskampen-2026">Se CupNavi live →</a>
              </div>
            </div>

            <aside className={styles.scoreCard} aria-label="CupNavi live preview">
              <div className={styles.scoreHead}><span>330 // LIVE</span><span>CUPNAVI</span></div>
              <div className={styles.scoreBody}>
                <strong>09:42  PLAN 2</strong>
                <p>NÄSTA MATCH<br/>ÖSK P2014 — MOTSTÅNDARLAG<br/>TABELLER • RESULTAT • INFO</p>
              </div>
            </aside>
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionHead}>
            <span className={styles.sectionNo}>01 // PRODUKTEN</span>
            <h2>Från första laget till sista finalen.</h2>
          </div>
          <div className={styles.featureGrid}>
            <article className={styles.feature}><span>01</span><h3>Bygg cupen</h3><p>Lag, klasser, grupper, planer, tider, domare, regler och slutspel samlas i samma flöde.</p></article>
            <article className={styles.feature}><span>02</span><h3>Skapa schemat</h3><p>CupNavi hjälper dig bygga ett spelbart schema med pauser, flera planer och slutspel.</p></article>
            <article className={styles.feature}><span>03</span><h3>Publicera direkt</h3><p>Dela en mobilvänlig cuplänk där publik och lag ser matcher, tabeller, resultat och cupinfo.</p></article>
            <article className={styles.feature}><span>04</span><h3>Följ favoritlag</h3><p>Besökaren väljer sina lag och får nästa match, plan och relevant information först.</p></article>
            <article className={styles.feature}><span>05</span><h3>Rapportera live</h3><p>Resultat, mål, assist och kort kan föras in under cupen och visas i den publika vyn.</p></article>
            <article className={styles.feature}><span>330</span><h3>Se läget direkt</h3><p>Tabeller och topplistor presenteras snabbt och tydligt med CupNavis egna Text-TV-lager.</p></article>
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionHead}>
            <span className={styles.sectionNo}>02 // TVÅ SIDOR</span>
            <h2>Byggd både för arrangören och cupområdet.</h2>
          </div>
          <div className={styles.split}>
            <article className={styles.panel}>
              <p className={styles.eyebrow}>Arrangör</p>
              <h3>Mindre administration. Mer kontroll.</h3>
              <p>Samla cupens viktigaste arbetsmoment i ett system i stället för kalkylblad, PDF:er och separata länkar.</p>
              <ul className={styles.list}>
                <li>Lag, grupper och klasser</li>
                <li>Schema, planer och domare</li>
                <li>A/B-slutspel och bronsmatch</li>
                <li>Roller, koder och publicering</li>
                <li>Import, export och cupinformation</li>
              </ul>
            </article>
            <article className={`${styles.panel} ${styles.panelDark}`}>
              <p className={styles.eyebrow}>Spelare • Ledare • Publik</p>
              <h3>Allt som behövs på matchdagen.</h3>
              <p>Den publika CupNavi-vyn är byggd för mobilen: snabbt in, rätt information först och minimalt letande.</p>
              <ul className={styles.list}>
                <li>Nästa match och rätt plan</li>
                <li>Favoritlag och laginformation</li>
                <li>Tabeller, resultat och slutspel</li>
                <li>Topplistor och liveinformation</li>
                <li>Hitta på cupområdet och dela cupen</li>
              </ul>
            </article>
          </div>
        </section>

        <section className={styles.finalCta}>
          <div>
            <p className={styles.eyebrow}>CupNavi</p>
            <h2>Din cup förtjänar mer än en PDF.</h2>
            <p>Planera, administrera och publicera cupen i ett sammanhållet matchdagssystem.</p>
          </div>
          <div className={styles.actions}>
            <a className={styles.primary} href="/admin">Öppna admin →</a>
            <a className={styles.secondary} href="/cup/slottskampen-2026">Se demo →</a>
          </div>
        </section>
      </div>
    </main>
  );
}
