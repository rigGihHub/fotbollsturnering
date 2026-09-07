# CupNavi v481 — Turso Failure & Recovery

## Problem som granskades
CupNavi återanslöt redan en misslyckad läsfråga en gång, men en trasig Turso-anslutning kunde ligga kvar i Streamlit-sessionen efter ett skrivfel eller commit-fel.

## v481
- Misslyckad Turso-connection kastas ur sessionen.
- SELECT/läsning får exakt ett kontrollerat återanslutningsförsök.
- Om även det försöket misslyckas kastas den nya anslutningen också.
- INSERT/UPDATE/DELETE och andra writes retryas aldrig automatiskt.
- `executemany` retryas aldrig efter write-fel.
- Commit-fel behandlas som okänt utfall och retryas aldrig automatiskt.
- Trasig rollback får inte maskera det ursprungliga felet.
- Nästa användaråtgärd får en ny Turso-connection och ska läsa färskt läge innan ny write.

## Varför ingen automatisk write-retry?
Om nätverket bryts precis efter att Turso tog emot skrivningen går det inte alltid att veta om operationen genomfördes. En blind retry kan då ge dubbletter eller dubbla matchhändelser. CupNavi väljer därför fail-safe.

## Oförändrat
- Ingen lokal SQLite-fallback i produktionsläge.
- Ingen schemaändring.
- Schema v32.
