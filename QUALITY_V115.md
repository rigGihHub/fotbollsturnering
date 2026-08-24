# CupNavi QUALITY V115

Version: 2026.08.24-115-QA-HOTFIX

## Scope
- QA-only hotfix for stale share regression test.
- `test_public_share_is_compact` now validates the current integrated global share entry point and lazy inline share panel instead of the pre-v111 implementation detail.
- No product behaviour, database schema, scheduling logic, or public UX changed.
- Release version synchronized across `app.py`, `VERSION.txt`, and `cupnavi_core/version.py`.

## Verification
- Python syntax compilation: PASS.
- Full pytest suite: PASS — 259 tests.
- GitHub update package verified independently after packaging.
