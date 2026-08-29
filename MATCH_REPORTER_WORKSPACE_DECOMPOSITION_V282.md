# CupNavi v282 — Match Reporter workspace decomposition

## Scope
The Streamlit orchestration for CupNavi Score, match events, referee centre and offline drafts has moved from `app.py` to `cupnavi_core/match_reporter_workspace_view.py`.

## Safety boundary
All protected writes remain in `app.py` behind injected callbacks. Result writes still use `update_match_result_if_unchanged`, event writes still use `update_player_match_stats_if_unchanged`, and referee acknowledgements remain an app-owned persistence action. No database schema or concurrency semantics were changed.

## Result
`render_match_reporter_view` is now a thin dependency boundary. The workspace module owns widgets, session-state orchestration, read-only repository calls and presentation behavior.
