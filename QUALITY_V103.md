# CupNavi QUALITY V103

Version: 2026.08.24-103-LOCKED-FOUNDATION

## Scope
- Sport is selected only when a tournament is created and is read-only afterwards.
- Locale/region, IANA timezone and country code are selected only at tournament creation and are read-only afterwards.
- Participant type is derived from the chosen sport at creation.
- Existing tournaments show a read-only foundation summary; sport rules can still be reset to the locked sport profile defaults.
- CupNavi persistent logo/header reduced on desktop and mobile.
- No database schema change.

## Verification
- Python syntax compilation: PASS.
- Full pytest suite: PASS — 218 tests.
- Regression tests added in `tests/test_locked_foundation_v103.py`.
