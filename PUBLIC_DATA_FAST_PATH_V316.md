# CupNavi v316 – Public data fast path

## Problem
After v315 the primary public navigation stays inside the active Streamlit session, but every public route still loaded the complete published match schedule plus full team rows before rendering its content.

That was unnecessary on Statistics and Playoffs when no favorite team is selected, and on Tables when final ranking is disabled.

## Change
- `public_core_snapshot()` now accepts `include_matches`.
- Statistics and Playoffs skip the published-match query unless a favorite team requires match data.
- Tables skips the published-match query when final ranking is disabled and no favorite team is selected.
- Matches, Cupinfo and information-screen mode keep loading matches as before.
- Team rows now use a compact public projection instead of `SELECT *`: identity, group/class and kit fields only.
- Cache keys include the match-loading mode so compact and full snapshots cannot collide.

## Behavior preserved
- Primary navigation and URL sync are unchanged.
- Follow-my-team still has full match data whenever a team is selected.
- Final ranking still receives match completion data when enabled.
- Match cards retain kit colors/patterns, referee and pitch labels.
- No persistence, schedule, result, playoff or concurrency logic changed.
