# CupNavi QUALITY V125

Version: 2026.08.24-125-COMPETITION-CLASS-DB-HOTFIX

- Repairs partial/mixed Turso deployments where v14 may be marked but competition_classes objects are missing.
- competition_classes() self-heals once and retries instead of crashing the public/admin UI.
- Adds regression coverage for a v14 marker with missing table/columns.
- No feature changes beyond database resilience.
