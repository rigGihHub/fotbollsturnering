# CupNavi QUALITY V97

Version: 2026.08.24-97-STABILITY-UX

## Scope
- Regression fix for public-view `KeyError: 'sport'` when an older tournament row lacks the v96 `sport` column.
- General safe row accessor added for backward-compatible reads from sqlite/libSQL rows and dictionaries.
- All direct public/admin tournament reads of the new `sport` field now use the safe accessor with `Fotboll` as legacy default.
- Added an idempotent v96 experience-schema compatibility bootstrap in `app.py` so a mixed/partial GitHub deployment can self-repair `sport`, check-in, audit/feed/notification, venue and referee-ack schema before rendering.
- Added a release integrity guard that warns Admin if `app.py` and `cupnavi_core/version.py` come from different releases.
- Database health display now checks against the minimum schema required by the running app build.
- No tournament scheduling/result logic changed.

## Root cause
The screenshot showed v96-era code reading `tournament['sport']` while the visible version badge still reported v92. That combination indicates release files/database migrations were not fully in sync. The public view crashed before it could fall back to a legacy sport.

## Similar-risk review
- `sport` reads: hardened.
- `teams.checked_in` / `teams.checked_in_at`: schema compatibility ensured before queries.
- `matches.original_scheduled_start`: schema compatibility ensured before updates.
- v96 tables `audit_log`, `cup_feed`, `notifications`, `venue_points`, `referee_acknowledgements`: created idempotently before use.

## Verification
- Python syntax compilation: PASS.
- Full pytest suite: PASS — 193 tests.
- New regression tests: `tests/test_stability_v97.py`.
- Legacy in-memory database without `sport` is repaired and retains `Fotboll` as default.
- Compatibility bootstrap is verified idempotent.
