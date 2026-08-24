# CupNavi – teknisk struktur från version 45

Version 45 påbörjar en stegvis refaktorering. `app.py` är fortfarande entrépunkt för Streamlit,
men ny ren affärslogik ska placeras i `cupnavi_core/` och testas utan Streamlit/Turso.

## Regel
- UI och routing: `app.py` (ska stegvis brytas ut senare)
- Testbar domänlogik: `cupnavi_core/`
- Automatiska tester: `tests/`
- CI: `.github/workflows/ci.yml`

Nästa tekniska steg är att bryta ut databas/repositories, scheduler och standings i separata moduler.
Det bör göras stegvis med tester runt befintligt beteende, inte som en stor omskrivning.

## V96
`cupnavi_core/experience.py` innehåller testbar domänlogik för sportprofiler, schemaeffektanalys, kvalitetsbetyg, förseningsplanering, slutspelsprognos och cupsummering. UI och persistens ligger fortsatt i `app.py` för att undvika en riskfylld storrefaktor samtidigt som funktionerna införs.
