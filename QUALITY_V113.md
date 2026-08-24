# CupNavi QUALITY V113

Version: 2026.08.24-113-QA-SYNC

## Scope
- QA hotfix only; no new product functionality.
- Aligns regression tests with the integrated share implementation introduced in v111.
- Ensures privacy tests reflect the player-name-only protection model.
- Ensures schema regression checks follow current schema v12.
- GitHub update package now contains the complete `tests/` directory as well as the complete `cupnavi_core/` directory to avoid stale test files in CI.

## Verification
- Python syntax compilation: PASS.
- Full pytest suite: PASS.
