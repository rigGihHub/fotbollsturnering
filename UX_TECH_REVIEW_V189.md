# CupNavi v.1.189 – UX/Logic/Performance/Release review

## Implemented
| Priority | Area | Evidence | Change |
|---|---|---|---|
| P1 | Logic/UX | Test tools were rendered in production cups | Production cups no longer render operational test controls; users are directed to create a Testkopia |
| P1 | Performance | Group tables used 2×N group queries in several views | Added tournament-wide 3-query group-table batch path |
| P1 | API performance | Standings and brackets contained N+1 queries | Standings use fixed-query batch input; brackets use two queries |
| P1 | Release integrity | RELEASE_MANIFEST.txt was stale | Manifest is generated from the release tree with SHA-256 hashes and checked in CI |
| P1 | Security | No automated dependency vulnerability gate | Added scheduled/on-push pip-audit workflow |
| P1 | Monitoring | /health returned ok without touching the DB | Health now probes DB latency and returns HTTP 503 on DB failure |
| P2 | UI consistency | Short user version plus internal build version appeared in normal UI | Only v.1.189 remains user-facing; technical build stays in diagnostics |
| P2 | Repo hygiene | Local DB/secrets could be accidentally committed | Added .gitignore for secrets, DBs, backups and build/cache artifacts |

## Not fully verified here
- Real physical iPhone/iPad/Android rendering.
- Live Turso latency and network-failure behavior.
- pip-audit against the online vulnerability database; CI is configured to perform this.
- Production-scale 10×/100× load test.

## Remaining highest-value work
1. Real end-to-end browser journeys beyond shell smoke.
2. Rate limiting for public feedback/login attempts.
3. Break direct UI SQL mutation paths into a domain/service layer.
4. Further split the very large public/admin render functions only where it reduces regressions.
5. Introduce production telemetry/error alerting to an external service when a provider is selected.
