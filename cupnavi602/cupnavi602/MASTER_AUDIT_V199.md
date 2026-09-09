# CupNavi v.1.199 – Master Product & Technical Audit

## Executive summary
CupNavi is no longer a small prototype. The repository already contains a broad tournament domain, public experience, role-based flows, PWA/API work, migrations, backup, security controls and a large regression suite. The largest verified constraint is now change risk: `app.py` is ~16.8k lines and contains several very large render/setup functions plus 20 historical CSS blocks. The next level should therefore be reached through controlled extraction and behavioral regression guards, not a rewrite.

## Evidence map
- VERIFIED: `app.py` is >16k lines.
- VERIFIED: `render_public_view` is >1,000 lines; `render_match_reporter_view` >500; `render_initial_tournament_setup` >450; `init_db` >400.
- VERIFIED: 20 `<style>` blocks remain, with v1.198 acting as final visual authority.
- VERIFIED: CI runs compile, pytest, migration, backup, browser, mobile-PWA, security and release-integrity checks.
- VERIFIED: server-side rate limiting exists and is used for feedback/login-related flows.
- VERIFIED: active-tournament switching had a rerun-state regression and was fixed in v1.197.
- LIKELY: large render functions increase regression risk and slow safe iteration.
- UNKNOWN: real production latency under 100/1,000/10,000 concurrent users; no production load evidence is present in this package.
- UNKNOWN: physical-device behavior across the full iOS/Android matrix.

## Product scorecard (code/repository evidence only)
| Area | Assessment | Confidence |
|---|---|---|
| Product breadth | Strong | High |
| UX structure | Improving, still complex in Admin | High |
| UI consistency | Stronger after v1.198, legacy CSS remains | High |
| Mobile | Good automated coverage, physical-device gap | Medium |
| Performance | Several optimizations/contracts exist; production scale unproven | Medium |
| Architecture | Transitional: Streamlit monolith + extracted core + FastAPI/PWA path | High |
| Code quality | Strong test intent, monolith remains main risk | High |
| Security | Solid baseline controls; external audit not evidenced | Medium |
| Accessibility | Explicit contracts/styles; full assistive-tech audit unproven | Medium |
| QA | Strong automated regression footprint | High |
| Scalability | Prepared directionally, not proven at large scale | Medium |

## Top 10 verified problems / constraints
1. `app.py` remains a very large change surface.
2. `render_public_view` is >1,000 lines.
3. Database initialization/migration compatibility still has a large app-level footprint.
4. Historical CSS remains layered even after visual consolidation.
5. Many Streamlit reruns/session-state transitions create navigation regression risk.
6. Some tests are source-contract tests rather than behavioral tests.
7. Public/Admin UI and PWA/API represent multiple presentation paths that require parity discipline.
8. Production-scale load characteristics are not verified.
9. Physical mobile-device accessibility/rendering is not verified.
10. Architecture is transitional; premature full rewrite would create more risk than value.

## Top 10 opportunities
1. Extract one UI domain at a time behind stable interfaces.
2. Convert fragile source-string tests to behavioral tests where possible.
3. Build an executable Critical User Journey regression layer.
4. Consolidate CSS only after screenshot/browser parity is available.
5. Move remaining direct UI data mutations toward services incrementally.
6. Add measured production telemetry before deeper performance work.
7. Add realistic load fixtures before infrastructure scaling decisions.
8. Expand browser E2E around Admin creation/publish/result flows.
9. Add accessibility automation plus manual screen-reader checklist.
10. Continue API/PWA parity as an escape hatch from Streamlit, not a big-bang rewrite.

## Prioritized backlog
### P0
- Protect tournament selection/navigation behavior with behavioral tests.
- Keep backup, lifecycle, permissions and destructive admin controls regression-guarded.

### P1
- Extract public rendering subdomains from `render_public_view`.
- Add executable tests for the most important end-to-end journeys.
- Gradually route mutations through service/domain functions.
- Add production telemetry/error reporting once provider/credentials are selected.

### P2
- Consolidate historical CSS after visual regression tooling is in place.
- Continue splitting setup/match-reporter functions where boundaries are clear.
- Add load-test fixtures and budgets.

### P3 / later
- Large framework rewrite. Do not do until product/scale evidence justifies it.
- Infrastructure for 100k users without measured need.

## First safe implementation
v1.199 converts the active-tournament selector's seed precedence into pure, testable UI logic and adds behavioral regression tests. This directly protects a recently observed user-facing failure without changing the database or business rules.
