# CupNavi 2026.09.04-451 – GO-LIVE READINESS

## Syfte
Göra sista steget före skarp cup tydligt och verifierbart utan att blanda ihop publiceringskvalitet med driftberedskap.

## Nytt
- Ny sektion **Skarpt läge** under admin → Kontroll.
- Kontrollerar produktionsdatabas (Turso), databasschema/kritiska tabeller, matchrapportörskod, lag, schema, publikvy, spelartrupper och att en testbar gruppspelsmatch finns.
- Endast verkliga driftkrav blockerar start. Saknade trupper varnar eftersom lagresultat fortfarande fungerar, men målskytt/assist blir ofullständigt.
- Varje blockerare/varning kan länka direkt till rätt adminområde.
- En aggregerad turneringsfråga används för go-live-status för att undvika många Turso-roundtrips.
- Inbyggt manuellt tvåmobilers-genrep för mål, ångra, samtidighet, nätavbrott och slutresultat.
- Genrepets checkboxar är uttryckligen sessionslokala och kan inte misstolkas som permanent revisionsbevis.

## Databas
Ingen schemaändring. Kräver fortsatt schema v32.
