# v1.298 – Schedule recovery view decomposition

- Flyttar den rangordnade UI-presentationen för schemats återställningsförslag till `cupnavi_core/schedule_recovery_view.py`.
- Behåller alla persistence-känsliga åtgärder i `app.py`: förlängda plantider, borttagna sena-startreservationer, ändrad extrapause och tillagd plan.
- `app.py` använder en tunn dependency-injected wrapper så befintlig `schedule_workspace_view` inte behöver ändra sitt kontrakt.
- Ingen schemaalgoritm, databasmodell, publiceringslogik eller concurrencylogik ändras.
