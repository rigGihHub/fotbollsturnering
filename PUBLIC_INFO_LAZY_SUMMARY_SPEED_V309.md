# CupNavi v1.309 – Public Info Lazy Summary Speed

## Fokus
UI-förenkling och snabbare publik Cupinfo utan ändringar i cupens kärnlogik.

## Ändringar
- Cupinfo återanvänder nu den redan hämtade `venue_points`-snapshoten i stället för att göra ett andra DB-anrop för Cupkarta.
- Slutlig Cupsummering är nu explicit opt-in via **Visa cupsummering**.
- Toppscorer- och laghämtning körs först när användaren faktiskt vill se summeringen.
- Summeringen visas i en tydlig avgränsad container i stället för en expander vars innehåll ändå exekverades i bakgrunden.

## Oförändrat
- Inga ändringar i schemaalgoritm, resultat, publicering, auth, DB-schema eller concurrency/CAS.
- Lagkontakter, funktionärer, erbjudanden, partners och feedback fungerar som tidigare.
