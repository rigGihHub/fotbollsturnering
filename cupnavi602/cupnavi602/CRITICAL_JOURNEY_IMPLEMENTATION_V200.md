# CupNavi v.1.200 – Critical Journey Hardening

## Implemented
- Public browser journey now verifies section-specific domain content.
- Added reusable UI-error guard.
- Extracted UI helper for creating persisted Testmiljö tournaments in browser tests.
- Added real Chromium regression test for active-tournament switching across rerun/reload.
- Existing Chromium/Firefox/WebKit lifecycle journey remains intact.

## Why
The previous E2E could pass a public section merely because no traceback was rendered. That did not prove that the correct content was visible. A recently observed active-tournament state regression also needed a browser-level guard rather than only a Python helper test.

## Acceptance criteria
- Each public main section renders expected domain content.
- Active tournament can switch between two persisted cups.
- The selected tournament survives a browser reload.
- Existing non-browser regression suite remains green.
- Existing three-browser lifecycle test remains collectable and runnable.

## Remaining risk
Full Chromium/Firefox/WebKit E2E is environment-dependent and GitHub Actions remains the final cross-browser source of truth.
