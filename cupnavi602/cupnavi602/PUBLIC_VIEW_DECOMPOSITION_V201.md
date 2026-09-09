# CupNavi v.1.201 – Public View Decomposition, Phase 1

## Problem
`render_public_view()` remained a 1,049-line Streamlit render function. Public desktop routing, mobile routing and URL section mapping were duplicated inside it. This increased regression risk and forced tests to inspect exact source strings.

## Evidence
- `render_public_view()` measured 1,049 lines before this change.
- Public section mappings existed as local dictionaries and hard-coded mobile links.
- Multiple tests were coupled to implementation details such as `nav1...nav5` and local mapping names.

## Change
Created `cupnavi_core/public_view_logic.py` containing pure, Streamlit-free navigation logic:
- canonical page specifications
- section → page resolution
- page → section mapping
- shared desktop/mobile navigation source of truth

`app.py` now consumes this logic rather than duplicating it.

## Result
- `render_public_view()` reduced to 1,034 lines in phase 1.
- Desktop and mobile navigation now share one canonical specification.
- Routing behavior has direct unit tests.
- Stale source-string tests were replaced by behavioral contracts.

## Regression scope
No tournament data, permissions, results, scheduling, tables, playoff logic, statistics or persistence behavior was changed.

## Next phase
Extract one rendering subdomain at a time, starting with the safest boundary (public information or public statistics orchestration), only after current browser E2E remains green.
