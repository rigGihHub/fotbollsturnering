# CupNavi v1.279 – Admin overview decomposition

## Goal
Reduce responsibility in `app.py` without changing the admin workflow, database schema, concurrency protections, or publication behavior.

## Changes
- Added `cupnavi_core/admin_overview_repository.py` for the batched admin-dashboard counter query.
- Added `cupnavi_core/admin_overview.py` for framework-agnostic admin overview logic:
  - preparation/workflow model
  - readiness state
  - control-center status summary
  - progress and attention items
  - competition-class progress caption
  - status/workflow HTML
  - next-step recommendation
- `app.py` retains Streamlit rendering, session state, navigation callbacks, fairness rendering, incidents, direct editing, publication controls, destructive actions, and test tools.
- Existing derived render caching and performance accounting stay in `app.py`; the repository owns only the SQL query contract.
- Updated architecture-sensitive regression tests to follow the extracted implementation instead of requiring logic to remain inline in `app.py`.

## Safety
- No database schema or migration changes.
- No auth changes.
- No result/event/team/group concurrency protections changed.
- No publication rules changed.
- No live deployment claim is made by this package.

## Verification
- 279 non-E2E test files passed in four batches.
- Python compilation passed for app/core/API/tests/E2E sources.
- Release manifest check passed.
- ZIP integrity check passed.
- Full browser E2E and physical-device testing were not run for this release.
