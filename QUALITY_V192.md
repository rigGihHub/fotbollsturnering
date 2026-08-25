# CupNavi v.1.192 – CI health dependency fix

Release: `2026.08.25-192-CI-HEALTH-DEPENDENCY`

## Scope
- Declares `httpx` as a development/CI dependency because `fastapi.testclient.TestClient` requires it through Starlette.
- Keeps `httpx` out of production `requirements.txt`; it is only needed by test/quality tooling.
- Adds a regression contract so the dependency cannot silently disappear while the health-contract script still uses `TestClient`.
- Fixes the critical Streamlit journey so Testmiljö is verified against persisted state during guided setup, then against the visible TESTMILJÖ marker after entering Admin.
- Regenerates the release manifest only after all v.1.192 files are finalized, preventing a stale manifest in CI.
- No tournament business logic, permissions, lifecycle rules, schema, result handling, or UI behavior is changed.

## Verification
Verification results are generated from the release candidate before packaging. GitHub Actions remains the source of truth for the clean hosted CI environment.
