# CupNavi v.1.209 – Match Reporter Audit / Phase 1

## Audit
`render_match_reporter_view()` is 520 lines.
`render_initial_tournament_setup()` is 466 lines.

Match Reporter was selected first because it combines more session-state transitions,
database reads/writes and result/event mutation paths in one function.

## Phase 1 implementation
The following pure logic is moved to `cupnavi_core/match_reporter_logic.py`:

- selection of matches where both source expressions resolve to real teams;
- projection of matches into the bulk result-entry table.

The same playable-match selection is now reused by both:
- CupNavi Score/result reporting;
- Matchhändelser.

## Explicitly unchanged
- optimistic locking;
- result persistence;
- autosave behavior;
- playoff/tie validation;
- event validation;
- notifications;
- audit logging;
- referee acknowledgements;
- offline drafts;
- permissions and authentication.

## Why this is safe
The extracted logic has no Streamlit or database imports and has direct behavioral tests.
It removes duplicate selection logic without changing the persistence boundary.

## Next candidate
Phase 2 should audit result-diff/validation preparation before saving. It should only be
extracted if the behavior can be covered with pure tests without weakening optimistic locking.
