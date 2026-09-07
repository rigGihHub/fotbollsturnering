# CupNavi v456 — Launch freeze audit

Version: `2026.09.07-492-BUTTON-LATENCY-III`

## Fokus
Sista statiska incidentgranskningen före skarpt tvåmobilers-genrep. Ingen ny produktfunktionalitet.

## Fix
- **Testmiljö är nu en blockerare i Skarpt läge.** Ett manuellt genrep kan alltså inte ge PASS på en cup som fortfarande är markerad som Testmiljö.
- Befintligt krav på Turso/cloud kvarstår som blockerare. Lokal SQLite är fortsatt tillåten för utveckling men kan inte godkännas för skarp start.
- Testverktyg/demodata är fortsatt spärrade till Testmiljö.
- Rapportörs-/domarkoder genereras slumpmässigt och saknar hårdkodad standardkod.
- Schema v32; ingen migrering.

## Audit
Granskade särskilt:
- lokal databasfallback och Turso-konfiguration
- test/demo-verktyg och miljögräns
- rapportörskoder
- go-live PASS/NO-GO
- bred exception/fallback-användning i kritiska flöden

Breda exceptions finns kvar främst vid UI-/kompatibilitetsgränser och go-live visar explicit fel om kontrollen inte kan köras. Ingen generell omskrivning görs i freeze-releasen eftersom det skulle öka regressionsrisken före genrep.

## Launchregel
Efter deploy av v456: kör v455/v456:s skarpa genrep mot Streamlit + Turso på minst två mobiler. Vid PASS fryses koden inför cupen. Ändringar efter PASS kräver nytt relevant genrep.
