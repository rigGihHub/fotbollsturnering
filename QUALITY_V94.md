# CupNavi QUALITY V94

Version: 2026.08.23-94-BRAND

## Scope
- User-selected CupNavi logo packaged locally in `assets/cupnavi_logo.png`.
- Persistent fixed branding visible across public, admin and match-reporter modes.
- Responsive placement: top-right on desktop, compact bottom-right on mobile.
- Global shell wording/icons made sport-neutral where appropriate (`CupNavi`, trophy/calendar instead of football-only branding).
- No database schema or tournament logic changes.

## Verification
- Python syntax compilation: PASS.
- Full pytest suite: PASS — 181 tests.
- Regression tests added in `tests/test_brand_v94.py`.
