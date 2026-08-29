# CupNavi v1.278 – Demo data service decomposition

## Mål
Fortsätta den kontrollerade nedbrytningen av `app.py` utan att ändra produktbeteende eller röra produktionsdataflöden.

## Ändring
- Ny `cupnavi_core/demo_data_service.py` med en Streamlit-oberoende `DemoDataService`.
- Test-/demodataflödet för gruppresultat, slutspel, spelstatistik, resultatreset, säker testkapacitet, schemaberedning och progressionsnivåer ligger nu i tjänsten.
- `app.py` behåller tunna kompatibilitetswrappers så befintliga anrop och UI-flöden inte behöver skrivas om.
- App-/DB-beroenden injiceras via `DemoDataDeps`; tjänsten importerar inte `app.py` och skapar ingen cyklisk modulkoppling.
- Produktionsskyddet bevaras: säker kapacitetsjustering gör inga skrivningar när turneringen inte är en testmiljö.

## Regressioner
Äldre källkodstester som krävde implementationen direkt i `app.py` har uppdaterats till att verifiera samma kontrakt i den nya modulen samt delegation från `app.py`.

## Databas
Ingen schemaändring och ingen migration.
