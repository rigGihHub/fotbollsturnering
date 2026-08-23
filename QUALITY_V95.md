# CupNavi QUALITY V95

Version: 2026.08.23-95-LOGO-POLISH

## Scope
- Replaced the previous rough logo implementation with a cleaner CupNavi wordmark/logo based on the generated concept rather than the copied screenshot.
- Logo asset is now a cropped transparent PNG in `assets/cupnavi_logo.png`.
- Persistent branding redesigned as a centered, integrated top brand bar that stays visible in all views.
- Responsive sizing for desktop and mobile, with extra top padding so content is not hidden behind the brand bar.
- No tournament logic or database schema changes.

## Verification
- Python syntax compilation: PASS.
- Full pytest suite: PASS.
- Regression tests added in `tests/test_brand_v95.py`.
