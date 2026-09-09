# CupNavi 2026.09.04-450-LIVE-GOAL-HARDENING

## Syfte
Go-live-härdning av målrapporteringen inför skarpt cup-test.

## Förbättringar
- Live-mål kan nu spara matchresultat och målskytt atomiskt i samma databastransaktion.
- Första live-målet kan starta från ett ännu tomt resultat och blir exempelvis 1–0 i samma skrivning.
- Ett misslyckande eller samtidighetskonflikt på resultat eller målskytt rullar tillbaka hela måloperationen.
- Match- och spelarägarskap verifieras server-side innan mål skrivs.
- Ett live-mål sätter matchen till Pågår och använder befintlig push-kö för målnotiser.
- Ångra senaste live-mål återställer både resultat och målskytt tillsammans.
- Avslutade matcher ändrar inte resultat när målskyttar kompletteras; där används fortsatt händelse-only-flödet.
- Livehändelser kan öppnas innan slutresultatet är sparat i Avancerad rapportering.

## Säkerhet / dataintegritet
- Befintlig optimistisk låsning behålls på både matchresultat och spelarstatistik.
- Transaktionen använder BEGIN i Turso och BEGIN IMMEDIATE lokalt i SQLite.
- Fel lag, fel spelare, negativt resultat och stale writes stoppas.
- Ingen schemaändring; schema v32 behålls.

## Tester
- Ny fokuserad v450-svit för första mål, bortamål, ångring, lagvalidering, atomisk transaktion och UI-kontrakt.
- Hela pytest-sviten passerar.
- compileall passerar.
- Performance contract passerar.
- Release manifest genereras och verifieras.

## Kvar före faktisk skarp cup
Efter deploy ska ett produktionslikt genrep göras mot riktig Streamlit/Turso-miljö med minst två samtidiga mobiler, publikvy och avsiktligt nätverksavbrott. Detta kan inte bevisas enbart av lokala/CI-tester.
