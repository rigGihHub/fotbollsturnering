# CupNavi v1.268 – Public mobile profiling + first decomposition

## Syfte
Fortsätta efter v1.267 med mätning av den faktiska publika Android-resan, samtidigt som första kontrollerade delen flyttas ut ur den stora `app.py` utan funktionsförändring.

## Ändringar
- Turneringsvy / Matcher mäts nu per delsteg: liveflöde, highlights, aktiva besökare, summering/delning, filter, matchhändelser och matchkort/väder.
- De senaste delstegsmätningarna visas under Admin → Prestandadiagnostik.
- Mätningen sparar också antal synliga matcher och separat DB-tid/anrop för fragmentet.
- Publika HTML-byggare för liveflöde, highlights och summeringsrutor har flyttats till `cupnavi_core/public_match_overview.py`.
- Den nya modulen är ren/pure: inga Streamlit-anrop och inga databasfrågor. Det minskar kopplingen i `app.py` utan en riskabel rewrite.
- Inga concurrency-skydd, dataintegritetskontroller eller långlivade cacher har ändrats.

## Hur resultatet ska användas
Efter deploy: öppna Turneringsvy → Schema & resultat på Android, gör både första laddning och en eller flera warm reruns. Gå därefter till Adminöversikt → Prestandadiagnostik och jämför delstegen. Optimera först den del som faktiskt dominerar.
