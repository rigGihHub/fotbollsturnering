import styles from "./home.module.css";

export default function Home() {
  return (
    <main className="page-shell">
      <div className={styles.home}>
        <section className={styles.hero}>
          <div className={styles.topline}>
            <span>CUPNAVI</span>
            <span>FÖR ARRANGÖR, LAG OCH PUBLIK</span>
          </div>

          <div className={styles.heroGrid}>
            <div>
              <p className={styles.eyebrow}>Cupadministration + matchdag</p>
              <h1>Hela cupen. Ett ställe.</h1>
              <p className={styles.lead}>
                Skapa cupen steg för steg, bygg spelschemat och publicera en mobilvy
                där lag och publik hittar rätt match, tid och plan direkt.
              </p>
              <div className={styles.actions}>
                <a className={styles.primary} href="/admin">Skapa eller administrera cup →</a>
                <a className={styles.secondary} href="/cup/slottskampen-2">Se publik cup →</a>
              </div>
            </div>

            <aside className={styles.scoreCard} aria-label="Förhandsvisning av publik CupNavi-vy">
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
            <span className={styles.sectionNo}>01 // SÅ FUNGERAR DET</span>
            <h2>Från första laget till sista finalen.</h2>
          </div>
          <div className={styles.featureGrid}>
            <article className={styles.feature}><span>01</span><h3>Bygg cupen</h3><p>Lag, klasser, grupper, planer, tider, domare, regler och slutspel samlas i ett tydligt flöde.</p></article>
            <article className={styles.feature}><span>02</span><h3>Skapa schemat</h3><p>Bygg ett spelbart schema med rätt pauser, planer, matchtider och slutspel.</p></article>
            <article className={styles.feature}><span>03</span><h3>Publicera</h3><p>Dela en mobilvänlig cuplänk med matcher, tabeller, resultat och praktisk information.</p></article>
            <article className={styles.feature}><span>04</span><h3>Följ favoritlag</h3><p>Besökaren väljer sina lag och får nästa match, plan och relevant information först.</p></article>
            <article className={styles.feature}><span>05</span><h3>Rapportera live</h3><p>Resultat, mål, assist och kort kan registreras under cupen och visas direkt.</p></article>
            <article className={styles.feature}><span>330</span><h3>Se läget direkt</h3><p>Tabeller och topplistor presenteras snabbt med CupNavis tydliga Text-TV-lager.</p></article>
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionHead}>
            <span className={styles.sectionNo}>02 // TVÅ LÄGEN</span>
            <h2>En arbetsvy för arrangören. En snabbvy för matchdagen.</h2>
          </div>
          <div className={styles.split}>
            <article className={styles.panel}>
              <p className={styles.eyebrow}>Arrangör</p>
              <h3>Stega igenom cupen utan att tappa överblicken.</h3>
              <p>Arbeta i en naturlig ordning och hoppa direkt till ett steg när du behöver ändra något.</p>
              <ul className={styles.list}>
                <li>Lag, grupper och klasser</li>
                <li>Schema, planer och domare</li>
                <li>Slutspel och regler</li>
                <li>Behörigheter och publicering</li>
                <li>Import, export och cupinformation</li>
              </ul>
            </article>
            <article className={`${styles.panel} ${styles.panelDark}`}>
              <p className={styles.eyebrow}>Spelare • Ledare • Publik</p>
              <h3>Rätt information först.</h3>
              <p>Den publika vyn är byggd för mobilen och matchdagen: kort väg till nästa match och minimalt letande.</p>
              <ul className={styles.list}>
                <li>Nästa match och rätt plan</li>
                <li>Favoritlag och laginformation</li>
                <li>Tabeller, resultat och slutspel</li>
                <li>Topplistor och liveinformation</li>
                <li>Karta, cupinfo och delning</li>
              </ul>
            </article>
          </div>
        </section>

        <section className={styles.finalCta}>
          <div>
            <p className={styles.eyebrow}>CupNavi</p>
            <h2>Bygg cupen. Publicera när den är klar.</h2>
            <p>Ett sammanhållet flöde från planering till matchdag.</p>
          </div>
          <div className={styles.actions}>
            <a className={styles.primary} href="/admin">Öppna admin →</a>
            <a className={styles.secondary} href="/cup/slottskampen-2">Se publik vy →</a>
          </div>
        </section>
      </div>
    </main>
  );
}
