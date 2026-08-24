# CupNavi QUALITY V121

Version: 2026.08.24-121-SHARE-FAIRNESS-HOTFIX

## Scope
- Replaced the share control with a same-page HTML Popover API panel with native light-dismiss (click outside closes).
- Share control does not open a new window/tab and remains fixed beside the CupNavi brand.
- QR image uses cached generation plus browser lazy loading/async decoding.
- Hardened fairness loading for Turso/libSQL: use full match rows through the proven SELECT * path, normalize tournament id to int, and prevent fairness analysis failures from crashing Admin.
- Added regression coverage for both the share interaction contract and the fairness failure path.

## Verification
- Python syntax compilation: PASS.
- Full pytest suite: 278 passed.
- Release manifest regenerated from the actual core/test contents.
