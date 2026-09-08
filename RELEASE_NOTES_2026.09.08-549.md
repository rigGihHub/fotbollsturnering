# CupNavi 2026.09.08-549 — Current Release Gate

## Fixed
- Synchronized `VERSION.txt`, `app.py`, and `cupnavi_core/version.py`.
- Corrected a real v548 packaging/version drift where core still reported v547.

## Release verification
- Added `scripts/run_current_release_gate.py`.
- Preserves the historical test archive instead of rewriting old release contracts.
- Runs all evergreen/non-release-specific tests.
- Explicitly replaces the obsolete v90 weather-on-by-default contract with the current opt-in weather/first-paint contract.
- Runs selected v540-v548 functional and safety contracts around schedule repair, highlights, actionable schedule errors, reporter correction/push safety, setup-driven event controls, large mobile scoreboard controls, and network/write resilience.
- Adds v549 current release/version synchronization checks.

## Gate result
- 303 evergreen tests passed, 1 obsolete weather-default assertion deselected and superseded.
- 23 current/recent functional and safety tests passed.
- compileall passed for `app.py` and `cupnavi_core`.

Historical release-specific tests remain in the repository and are not part of the current release gate when they assert an exact obsolete release version or superseded source-level UI contract.
