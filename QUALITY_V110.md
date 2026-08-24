# CupNavi QUALITY V110

Version: 2026.08.24-110-TESTDATA-QA

## Scope
- Fixes stale CI regression expectations from v92/v106 that no longer matched current v109 behavior.
- Adds progressive complete demo/test-data states: half group stage, full group stage, half playoffs, completed cup.
- Demo seed now covers portal codes, responsible contacts, split player names/birth years, protected player sample, sponsors, functionaries, offers, venue points, notifications, team messaging, age-class configuration and public information.
- Test progress can rebuild schedule and reset only results/events before applying the selected state.
- No database schema change.

## Verification
- Python syntax compilation: PASS.
- Full pytest suite: PASS — 248 tests.
