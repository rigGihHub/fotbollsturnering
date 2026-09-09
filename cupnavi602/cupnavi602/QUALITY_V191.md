# QUALITY V191
Release: 2026.08.25-191-BEAUTIFY-FULL-E2E

## Beautify
- Consolidated functional design tokens for color, spacing, radii, surfaces, borders, states and typography.
- Removed gradient/glass/pill styling from the persistent brand and reduced header obstruction.
- Standardized primary/secondary button treatment, inputs, focus states, containers, expanders, alerts, metrics, tabs and tables.
- Added reduced-motion support and stronger keyboard focus.
- Desktop public navigation is text-first; mobile public navigation now has full five-section parity including Cupinfo.
- Added action-oriented empty states for key public/admin flows.
- Public Streamlit and standalone PWA now share a restrained visual vocabulary.
- Domain colors that communicate playoff qualification remain unchanged.

## Full E2E
- Expanded the Playwright critical journey to:
  Admin → create Testmiljö → generate class/team/group/roster/referee data → build complete schedule/results/playoff → verify DB persistence → public schedule/table/playoff/statistics/info → Matchrapportör test-only access.
- The critical journey is configured for Chromium, Firefox and WebKit in GitHub Actions.
- Each browser journey now also opens the completed cup in a 390×844 mobile public context and checks five-section navigation plus horizontal overflow.
- A local Playwright run was attempted but exceeded the available execution window; CI remains the verification point for the three browser engines.

## Local gates
- Full unit/regression suite passes: 622/622 collected test items.
- Python compile passes.
- Schema contract passes.
- PWA installability contract passes.
- Release manifest check passes.
- API health contract passes.
