import styles from "./home.module.css";

export default function Home() {
  return (
    <main className={styles.home}>
      <section className={styles.hero} aria-labelledby="home-title">
        <div className={styles.heroCopy}>
          <p className={styles.kicker}><span className={styles.kickerDot} /> CUPNAVI · FÖR HELA CUPDAGEN</p>
          <h1 id="home-title">Från första planen till sista matchen.</h1>
          <p className={styles.lead}>Skapa cupen, lägg schemat och ge alla en tydlig plats för matcher, tabeller och resultat.</p>
          <div className={styles.actions}>
            <a className={styles.primary} href="/admin">Skapa en cup <span aria-hidden="true">↗</span></a>
            <a className={styles.secondary} href="/cup/slottskampen-6">Se en exempelcup <span aria-hidden="true">→</span></a>
          </div>
          <p className={styles.actionHint}>Arrangören planerar. Lag och publik följer samma cup i mobilen.</p>
        </div>
        <div className={styles.heroVisual} aria-hidden="true">
          <div className={styles.visualOrbit} />
          <img src="/cupnavi-emblem-v2642.png" width="160" height="160" alt="" />
          <div className={styles.visualBoard}>
            <div className={styles.boardTop}><span>CUPDAG</span><span>01 / 03</span></div>
            <div className={styles.boardRows}>
              <span><b>01</b> Matcher <i>→</i></span>
              <span><b>02</b> Tabeller <i>→</i></span>
              <span><b>03</b> Resultat <i>→</i></span>
            </div>
            <div className={styles.boardBottom}>Rätt tid. Rätt plan. Rätt match.</div>
          </div>
        </div>
      </section>

      <section className={styles.how} aria-labelledby="how-title">
        <div className={styles.sectionTitle}>
          <p>EN CUP I TRE STEG</p>
          <h2 id="how-title">Enklare att ordna. Enklare att följa.</h2>
        </div>
        <div className={styles.steps}>
          <article><span>01 / SKAPA</span><h3>Samla allt</h3><p>Lägg in lag, grupper, planer och regler i samma arbetsflöde.</p></article>
          <article><span>02 / PLANERA</span><h3>Bygg schemat</h3><p>Få ordning på tider, matcher och slutspel innan cupen börjar.</p></article>
          <article><span>03 / GENOMFÖRA</span><h3>Dela och rapportera</h3><p>Publicera cuplänken och uppdatera resultaten under matchdagen.</p></article>
        </div>
      </section>

      <section className={styles.modes} aria-labelledby="modes-title">
        <div className={styles.sectionTitle}>
          <p>TVÅ VYER · SAMMA CUP</p>
          <h2 id="modes-title">Bygg bakom kulisserna. Visa det viktiga på läktaren.</h2>
        </div>
        <div className={styles.modeGrid}>
          <article className={styles.organizer}>
            <div className={styles.modeHead}><span>FÖR ARRANGÖREN</span><strong>01</strong></div>
            <h3>Full koll på cupen.</h3>
            <p>Skapa, planera och justera i en arbetsvy som visar vad som återstår.</p>
            <div className={styles.tags}><span>Lag & grupper</span><span>Schema & planer</span><span>Slutspel</span></div>
          </article>
          <article className={styles.visitor}>
            <div className={styles.modeHead}><span>FÖR LAG & PUBLIK</span><strong>02</strong></div>
            <h3>Hitta rätt direkt.</h3>
            <p>En mobilvy med matcher, tabeller, resultat och information om cupdagen.</p>
            <div className={styles.tags}><span>Hitta ditt lag</span><span>Nästa match</span><span>Resultat</span></div>
          </article>
        </div>
      </section>

      <section className={styles.finish} aria-label="Kom igång">
        <div><span>REDO ATT BÖRJA?</span><h2>Gör plats för matchdagen.</h2></div>
        <a href="/admin">Öppna CupNavi <span aria-hidden="true">↗</span></a>
      </section>
    </main>
  );
}
