# CupNavi 2026.08.21-73-STABILISERING2

Fokus: separera schemadomän från Streamlit/UI.

- Ny `ScheduleRepository`.
- Gruppmatchskapande läser/skriver via repository.
- Schemagenerator hämtar domare, resepreferenser och matcher via repository.
- Schemagenerator sparar hela schemapasset via en central atomisk repository-metod.
- Schemavalideringen hämtar schemalagda matcher via repository.
- Ny ren `schedule_domain.py` för cupdatum, matchlängd, förlängning och direkta team-källor.
- Repository och domänlogik har egna tester mot SQLite in-memory.
- Publikt och administrativt användarflöde är avsiktligt oförändrat.
