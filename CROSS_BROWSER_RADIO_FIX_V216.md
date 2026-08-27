# CupNavi v.1.216 – Cross-browser Testmiljö Radio E2E Fix

GitHub Actions showed that Playwright `check(force=True)` on Streamlit's hidden
React-Aria radio input could complete its click without changing selected state,
notably in Firefox and in the active-tournament Chromium journey.

The E2E helper now scopes to the creation form's `stRadio` component, clicks the
visible `label` for `Testmiljö`, waits briefly for Streamlit's rerender, reacquires
the semantic radio input and verifies `is_checked()`.

The stale v1.210 source contract that explicitly required `.check(force=True)`
has been updated so the regression suite no longer enforces the broken approach.

No CupNavi application business logic changes in this release.
