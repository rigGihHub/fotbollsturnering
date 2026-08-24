# CupNavi QUALITY V112

Version: 2026.08.24-112-CONTROL-ACCESSIBILITY

## Scope
- Optional Cup Control Center with operational status and incident handling.
- Optional scorer leaderboard, assist leaderboard and yellow/red-card statistics per tournament.
- Schedule fairness score with transparent findings for rest, early/late starts and venue changes.
- Accessibility controls: high contrast, larger text, 44px targets, focus-visible styling, screen-reader live status and future RTL direction helper.
- Functionary shift scheduling.
- Optional public medical preparedness, lost & found and visitor accessibility information.
- Schema migration v12.

## Verification
- Python syntax compilation: PASS.
- Full pytest suite: PASS — 254 tests.
- New regression tests in `tests/test_control_accessibility_v112.py`.
- Legacy migration tests made forward-compatible without weakening their original migration contracts.
