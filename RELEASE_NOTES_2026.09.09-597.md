# CupNavi v597 – RELEASE GATE CLEANUP & FULL RELEVANT REGRESSION

Version: `2026.09.09-597-RELEASE-GATE-CLEANUP-FULL-REGRESSION`

- Classified all six failures from the v596 selected gate.
- Confirmed they were superseded copy/navigation/version assertions, not product regressions.
- Replaced those selected assertions with semantic current-state contracts.
- Added startup/version sync regression coverage.
- Added current Planer & tider, Domare, Schema, Regler, Text-TV table and Lag-flow contracts.
- Kept historical test files unchanged.
- No deployment performed.

## Verification
- `python -m py_compile app.py cupnavi_core/version.py scripts/run_current_release_gate.py tests/test_current_release_gate_v597.py`: PASS.
- v597 semantic current-state contract: 8 passed.
- Evergreen gate: 302 passed, 2 deliberately deselected superseded historical assertions.
- Selected functional/safety/current UX gate: 157 passed.
- Current release gate: PASS with 0 selected failures.
- Historical release-specific tests remain in the repository and are not rewritten or deleted.
