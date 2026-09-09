# CupNavi v.1.202 – Public View Decomposition Phase 2

## Scope
Phase 2 extracts the full public Cupinfo renderer from `app.py` into
`cupnavi_core/public_info_view.py`.

## Before
- Cupinfo implementation: ~241 lines embedded in the main application file.
- Public info queries, practical information, sponsors, offers, team/functionary
  contacts, cup summary and feedback UI all lived in `app.py`.

## After
- `app.py` keeps a thin `@st.fragment` adapter.
- Full Cupinfo presentation lives in a dedicated module.
- Database access, domain helpers, rate limiting and persistence functions are
  injected from the application layer.
- No database schema, permissions, business rules or public behavior changed.
- Existing Streamlit fragment isolation is preserved.

## Why this boundary
Cupinfo already had a clear function boundary and lower coupling than the
match renderer. Moving it first reduces main-file change surface without
touching scheduling, results or lifecycle logic.

## Regression
Legacy source-contract tests were redirected to the new module while preserving
their existing assertions for sponsors, offers, venue information, contact
links, feedback rate limiting and performance metrics.

## Next candidate
Phase 3 should target public statistics orchestration or a bounded subsection
of the match renderer, depending on browser/E2E results.
