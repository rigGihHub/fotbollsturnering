# CupNavi – Streamlit → Next feature-parity audit

Status: 2026-09-13. This is a product-function audit, not a visual component count. A feature is only marked **Transferred** when the current Next/PWA flow exposes the equivalent user outcome; old Python modules merely remaining in `cupnavi_core/` do not count.

## Executive result

**No: all Streamlit functionality has not yet been transferred.** The core tournament setup/run flow is now substantially present in Next, but several useful Streamlit-era public, team/role and match-day capabilities are still partial or missing. New feature work should not outrank the P0/P1 parity gaps below.

## Admin / tournament creation

| Capability | Next status | Evidence / note |
|---|---|---|
| Create cup manually | **Transferred** | `cup-create-launcher.tsx`, `/api/admin/cups` |
| Create cup from photo/PDF/TXT, multiple files | **Transferred** | `cup-create-launcher.tsx`, `ai_cup_document_import`, review before commit |
| Saved first-import snapshot | **Transferred** | `tournament_setup_imports`; used by playoff/pitch review and import summary |
| Teams CRUD | **Transferred** | `admin-workspace.tsx`, admin API |
| Groups CRUD + team assignment | **Transferred** | `admin-workspace.tsx`, group admin repository |
| Team CSV/XLSX import with preview | **Transferred** | `import-admin.tsx`, `import_repository.py` |
| Later schedule revision from photo/PDF with change diff | **Transferred in current parity block** | `schedule-revision-import.tsx`; exact-match review + atomic commit + stale-data guard |
| Later group/photo-only revision workflow | **Missing** | No dedicated Next review/diff flow for a later group-draw photo |
| Cup trash / restore / empty trash | **Transferred / improved** | lifecycle `trashed`/`purged`, owner UI |

## Rules, venues and scheduling

| Capability | Next status | Evidence / note |
|---|---|---|
| Venue/pitch setup | **Transferred** | `venue-admin.tsx` |
| Pitch opening windows per cup day | **Transferred** | manual UI + document `pitch-window-import-review.tsx` |
| Match duration, breaks, team rest, points/tiebreak | **Transferred** | `rules-admin.tsx` |
| Manual schedule editing | **Transferred** | `schedule-admin.tsx` |
| Schedule conflict analysis | **Transferred** | `schedule_conflicts.py`, surfaced in Next |
| Deterministic schedule proposal + review | **Transferred** | `schedule_proposal_repository.py`, `schedule-admin.tsx` |
| Full-match-inside-pitch-window validation | **Transferred / fixed** | current scheduler contract |
| Conflict repair suggestions equivalent to older Streamlit guidance | **Partial** | Next identifies conflicts and auto-proposes a schedule, but does not expose all old targeted repair guidance/actions |
| Schedule revision compare-before-overwrite | **Transferred in current parity block** | new atomic revision route; rejects stale review and new hard conflicts |

## Playoffs

| Capability | Next status | Evidence / note |
|---|---|---|
| Configure playoff format/tie rules | **Transferred** | `playoff-admin.tsx` / playoff API |
| Import playoff tree from document | **Transferred** | `playoff-import-review.tsx`, transactional source resolution |
| Group-place / winner / loser dependencies | **Transferred** | `playoff_import_repository.py` |
| Validate bracket dependencies | **Transferred** | `bracket_validation` used on import |
| Old Streamlit downstream-result correction guidance / recovery | **Missing in Next UI** | Streamlit contracts reference dependency guidance, transitive impact and “Återställ oanvänd match”; no equivalent current Next control found |

## Match day / reporting

| Capability | Next status | Evidence / note |
|---|---|---|
| Enter final score | **Transferred** | `publish-reporting-admin.tsx` |
| Penalty result for tied knockout | **Transferred** | same UI/API |
| Fast mobile +/- score reporter | **Missing** | Streamlit contract had quick-score callbacks; Next currently uses number inputs |
| Register scorer, assist, yellow/red cards per player | **Missing in current Next reporting UI** | public API can display persisted statistics, but `publish-reporting-admin.tsx` currently only edits score/penalties |
| Match status controls / reset quick result | **Missing/partial** | older reporter workspace had explicit status and reset actions |
| Referee CRUD + assignment | **Transferred** | `referee-admin.tsx` |
| Dedicated cup-day operational pulse (now/problems/next 45 min) | **Missing** | present in older Streamlit performance contract, no equivalent Next admin module found |

## Organizer/team access

| Capability | Next status | Evidence / note |
|---|---|---|
| Owner + organizer authenticated admin | **Transferred** | organizer sessions and tournament membership API |
| Role codes / delegated limited-role access | **Missing in Next UI** | Streamlit `admin_role_codes_view.py` remains; no current Next role-code module found |
| Team portal/checklist | **Missing** | Streamlit `team_portal_view.py` contract remains; no equivalent Next page/component found |
| Team check-in flow | **Partial/backend field only** | public tournament still has `enable_team_checkin`, but no full Next team check-in journey found |

## Publication, PDF and export

| Capability | Next status | Evidence / note |
|---|---|---|
| Publication readiness / blockers | **Transferred** | `publish-reporting-admin.tsx` |
| Publish / unpublish | **Transferred** | same module |
| Admin PDF/export | **Transferred** | export API + admin export module |
| Public “create/download cup program PDF” | **Missing** | old Streamlit performance contract explicitly guards public PDF; current `PublicCupView.tsx` has no public PDF action |

## Public cup experience

| Capability | Next status | Evidence / note |
|---|---|---|
| Match list/cards | **Transferred** | `PublicCupView.tsx`, `MatchCard.tsx` |
| Tables | **Transferred** | `TextTvStandings.tsx` |
| Playoff display | **Transferred** | public bracket cards |
| Statistics / scorers / assists / cards / fairness | **Transferred for persisted data** | public statistics tab |
| Multiple favorite teams | **Transferred** | local favorites in `PublicCupView.tsx` |
| Next match for favorite teams | **Transferred** | matchday hero |
| Family next-step timeline across several favorite teams | **Partial** | favorites exist, but old dedicated family timeline/next-step logic is not reproduced fully |
| Travel guidance between successive family matches | **Missing** | old `build_family_travel_guidance` contract; no equivalent Next computation/UI found |
| Map link to next pitch | **Transferred** | matchday hero if venue URL exists |
| Weather | **Partial** | cup-level `WeatherShareCard`; old match-specific/lazy weather actions are not fully reproduced |
| Per-match event detail (scorers/cards) | **Missing/partial** | top lists exist, but current match cards do not expose old per-match event detail flow |
| Share cup | **Transferred** | Web Share / clipboard |
| Browser notification permission UI | **Partial** | permission can be requested; this is not yet proof of the older end-to-end notification behavior |
| Public cup information/venue points | **Transferred** | Cupinfo tab |
| PWA/mobile shell | **Transferred** | Next PWA boot + mobile nav |

## Priority order from this audit

1. **P0 – match reporting parity:** player events (goals, assists, cards), fast mobile score controls, match status/reset.
2. **P0 – playoff correction safety UI:** downstream dependency impact and safe recovery controls.
3. **P1 – role/team operations:** role codes, team portal, check-in.
4. **P1 – public parity:** public PDF, per-match events, family timeline/travel guidance, match-specific weather.
5. **P1 – later setup revisions:** group/photo revision and richer conflict repair guidance.
6. **P2 – polish/parity edge cases:** notification delivery and remaining secondary Streamlit conveniences.

## Rule for future migration work

Do not mark a Streamlit feature transferred because its Python helper still exists. Require: (1) reachable Next/PWA UI, (2) API/write-path if applicable, (3) review/safety behavior at least as strong as the old flow, and (4) a maintained regression test. Remove an item from this audit only after those four conditions are met.
