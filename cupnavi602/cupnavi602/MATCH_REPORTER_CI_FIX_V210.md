# CupNavi v.1.210 – CI Browser Fix + Match Reporter Hardening Phase 2

## GitHub Actions failures addressed

### 1. Public match page crash
Cross-browser E2E showed:
`AttributeError: 'sqlite3.Row' object has no attribute 'get'`

The failure originated in `cupnavi_core.experience.match_duration_minutes()`.
The helper accepted Mapping-like tournament rules but assumed `.get()` existed.
SQLite rows support key access but not `.get()`.

Fix:
- `_rule_value()` now supports both dictionaries/mappings and sqlite3.Row.
- A regression test creates a real sqlite3.Row and verifies match duration.

### 2. Testmiljö selection timeout
The active-tournament E2E clicked the rendered text node `Testmiljö`.
A Streamlit `<details>` element could intercept pointer events.

Fix:
- E2E targets the semantic radio control.
- Uses `check(force=True)` and verifies `is_checked()`.
- The brittle text-node click is removed.

## Match Reporter Phase 2
Bulk result preparation is extracted to
`cupnavi_core.match_reporter_logic.prepare_bulk_result_update()`.

It handles:
- changed/not-changed detection;
- complete-pair result guidance;
- group-stage removal of playoff-only fields;
- tied playoff penalty validation;
- lottery winner selection;
- construction of the expected optimistic-lock snapshot.

Persistence and `update_match_result_if_unchanged()` remain in app.py.

## Safety
No database schema, permissions, result persistence, notification behavior,
audit logging or optimistic-lock conflict resolution is moved or removed.
