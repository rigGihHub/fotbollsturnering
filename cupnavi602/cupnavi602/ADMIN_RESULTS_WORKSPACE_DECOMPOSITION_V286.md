# CupNavi v286 – Admin Results Workspace Decomposition

Version: `2026.08.29-286-ADMIN-RESULTS-WORKSPACE-DECOMPOSITION`

## Scope

The admin **Matcher och resultat / Resultat** workspace has been extracted from `app.py` into a dedicated presentation/orchestration module while preserving the existing persistence and concurrency boundary.

## Changes

- Added `cupnavi_core/admin_results_view.py` for the admin result editor, progress/status presentation, search-focus context, lazy full-schedule view, playoff tie guidance and pure preparation of edited result rows.
- Added `cupnavi_core/admin_results_repository.py` for the read-only result-workspace queries for matches, referees and teams.
- Kept `update_match_result_if_unchanged`, goal-push enqueue, published-match synchronization, feed entries and team notifications in `app.py` behind the injected `_save_admin_result_updates` callback.
- Preserved partial-score protection, playoff penalty validation, lottery-winner handling, referee-only updates, optimistic-lock snapshots and conflict messages.
- Updated source-location contract tests to follow the new module boundary without weakening behavior checks.

## Regression coverage

- Added `tests/test_v286_admin_results_workspace_decomposition.py` with focused coverage for module boundaries, read-only repository ownership, referee-only updates, partial score protection and invalid tied penalty scores.
- All 286 top-level `tests/test_*.py` files pass in five batches.
- `compileall` passes for app/core/API/tests/E2E.
- Release manifest generation/check and ZIP integrity are verified before delivery.

## Not verified in this environment

- Full browser E2E execution.
- Physical Android/iPhone testing.
- Live Streamlit deployment.
