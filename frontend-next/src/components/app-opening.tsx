import styles from "./app-opening.module.css";

export default function AppOpening({ waiting = false }: { waiting?: boolean }) {
  return (
    <main className={styles.page}>
      <section className={styles.card} aria-labelledby="app-opening-title">
        <div className={styles.pitch} aria-hidden="true"><span /></div>
        <img className={styles.emblem} src="/cupnavi-emblem-v2642.png" width="96" height="112" alt="" />
        <p className={styles.eyebrow}>TURNERINGEN I FICKAN</p>
        <h1 id="app-opening-title">Snart är du inne.</h1>
        <p className={styles.intro}>Vi öppnar din cupöversikt.</p>
        <div className={styles.status} role="status" aria-live="polite" aria-atomic="true">
          <span className={styles.spinner} aria-hidden="true" />
          <span>{waiting ? "Anslutningen tar lite längre tid" : "Öppnar CupNavi"}</span>
        </div>
        <p className={styles.hint}>Du kommer vidare automatiskt.<br />Din sparade inloggning finns kvar.</p>
      </section>
    </main>
  );
}
