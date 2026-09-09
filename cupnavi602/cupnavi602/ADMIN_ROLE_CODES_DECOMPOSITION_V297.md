# CupNavi v1.297 – Admin role codes decomposition

## Scope
The tournament-scoped Match Reporter and Referee access-code cards were extracted from `app.py` into `cupnavi_core/admin_role_codes_view.py`.

## Architecture
The new view owns the presentation and interaction flow: status, generation/regeneration buttons, explicit regeneration confirmation, one-time display of the newly generated code, and session-state keys.

Credential persistence remains in `app.py` through `_rotate_admin_role_code()`. Salt/hash generation, insert/update, transaction handling and commit were deliberately not moved into the view module.

## Behaviour preserved
- Four-digit code generation.
- Separate tournament-scoped credentials for Match Reporter and Referee.
- Explicit confirmation before an existing code is regenerated.
- Immediate invalidation semantics through the existing credential hash rotation.
- Newly generated code is shown only through the existing session-state flow.
- Two peer cards remain under Admin → Domare.

## Risk
No database schema, authentication contract, scheduler, result engine, publication flow or concurrency/CAS behaviour was changed.
