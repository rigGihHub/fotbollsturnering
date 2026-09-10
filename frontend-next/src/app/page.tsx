export default function Home() {
  return (
    <main className="page-shell landing-shell">
      <section className="landing landing--editorial">
        <div className="landing__issue"><span>CN//HOME</span><span>PUBLIC MATCHDAY</span></div>
        <p className="kicker">CupNavi</p>
        <h1>Cupdagen. Samlad.</h1>
        <p className="landing__lead">Matcher, tabeller, planer och liveinfo i en snabb publikvy byggd för mobilen på cupområdet.</p>
        <div className="landing__cards">
          <article><span>01</span><strong>Följ dina lag</strong><p>Välj flera favoritlag och få nästa match först.</p></article>
          <article><span>02</span><strong>Hitta rätt</strong><p>Plan, tid och matchstatus utan att leta i ett PDF-program.</p></article>
          <article><span>330</span><strong>Se läget live</strong><p>Tabeller och resultat med CupNavis Text-TV-lager.</p></article>
        </div>
        <p className="landing__hint">Öppna cupen via länken som arrangören har delat.</p>
        <p className="landing__admin-link"><a href="/admin">Arrangör? Öppna admin →</a></p>
      </section>
    </main>
  );
}
