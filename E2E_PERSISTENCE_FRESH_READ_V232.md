# CupNavi v.1.232 – E2E Persistence & Fresh-Read Hardening

## Failure 1: tournament missing immediately after submit
The E2E helper previously assumed the SQLite row existed immediately after a fixed UI wait.
It now polls the real E2E database for up to 20 seconds and still requires the persisted
row to have `environment_type=test`. This preserves the real UI creation contract while
removing a browser/Streamlit commit timing race.

## Failure 2: direct public URL briefly sees no published tournament
The completed-cup fixture intentionally writes SQLite directly from the pytest process.
A fresh public browser could briefly receive a server render that did not yet observe that
external commit. `wait_for_public_cup()` now retries the actual direct URL on the transient
empty-public state instead of failing immediately. It still requires the exact cup hero and
does not accept the empty state.

In CUPNAVI_E2E mode the app also clears render-local query/derived caches immediately before
mode/tournament resolution. Production behavior is unchanged.

## Verification
- delayed SQLite persistence test;
- source contracts for create polling and public reload;
- E2E cache-clear ordering contract;
- full non-E2E regression suite.
