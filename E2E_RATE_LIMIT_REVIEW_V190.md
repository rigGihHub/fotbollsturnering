# CupNavi v.1.190 – E2E & rate limiting

## Implemented
- Database-backed fixed-window rate limiting for failed Admin login: 8 attempts / 10 minutes.
- Database-backed fixed-window rate limiting for failed Matchrapportör login: 12 attempts / 10 minutes.
- Public feedback: 5 accepted submits / 10 minutes per cup/client key.
- Raw IP addresses are not stored by the limiter; the client identity is SHA-256 hashed.
- Migration v23 creates the rate_limits table.
- Test-only reporter code 123 remains available for Testmiljö and remains restricted to Testmiljöer.
- New Playwright critical Streamlit journey:
  Admin → create Testmiljö → verify TEST badge → Matchrapportör → login with test code → verify test-only scope.
- Critical journey is configured for Chromium, Firefox and WebKit in GitHub Actions.
- CUPNAVI_DB_PATH allows the E2E suite to use an isolated disposable database.

## Verification boundary
The unit/regression suite, schema, PWA, manifest and health contracts were run locally.
The three-engine Playwright journey is committed to CI but was not executed locally in this environment.
