# CupNavi QUALITY V109

Version: 2026.08.24-109-AGECLASS-UX

## Scope
- Weather forecast enabled by default in public match view.
- Persistent share action integrated beside the fixed CupNavi brand and follows scroll.
- Public tournament view no longer shows the build/version badge.
- Streamlit generic input instruction text ("Press enter to submit form") is hidden.
- Date selections show weekday abbreviations (sv: mån–sön, en: Mon–Sun).
- Multiple age classes per tournament supported with tournament configuration, team assignment, group assignment, safe group placement and public age-class filtering.
- Schema migration v11 adds age-class storage and indexes.

## Verification
- Python syntax compilation: PASS.
- Full pytest suite: PASS — 245 tests.
- Regression tests added in tests/test_ageclass_ux_v109.py.
