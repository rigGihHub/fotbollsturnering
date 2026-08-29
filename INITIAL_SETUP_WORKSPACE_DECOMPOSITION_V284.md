# CupNavi v284 – Initial setup workspace decomposition

Version: `2026.08.29-285-SCHEDULE-WORKSPACE-DECOMPOSITION`

## Ändrat
- Flyttat den guidade initiala turneringssetupens Streamlit-presentation och orkestrering från `app.py` till `cupnavi_core/initial_setup_view.py`.
- `app.py` behåller befintliga persistence-/servicefunktioner och injicerar dem via `InitialSetupDependencies`.
- Databas-/autosave-kontrakt, klasshantering, plan-/restidskonfiguration, formatrekommendationer, regler, prioriteringar, serviceval och slutlig kontroll använder samma underliggande callbacks som tidigare.
- Ingen schemaändring eller migration.

## Riskavgränsning
- Ingen schemagenereringsmotor eller concurrency-/CAS-logik har flyttats.
- Extraktionen är en strangler-refaktor: befintlig `render_initial_tournament_setup(...)` finns kvar som tunn wrapper i `app.py`.

## Verifiering
- Fokus- och regressionssvit körs i releasearbetet.
- Browser-E2E, fysisk mobiltest och live-deployment verifieras inte av denna release i sig.
