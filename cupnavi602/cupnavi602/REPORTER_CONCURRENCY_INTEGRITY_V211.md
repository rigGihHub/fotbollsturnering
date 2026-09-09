# CupNavi v.1.211 – Reporter Concurrency & Result Integrity

## Goal
Strengthen the result-reporting safety boundary before moving any persistence
logic out of app.py.

## Implemented

### Canonical optimistic-lock snapshot
`cupnavi_core.match_reporter_logic.result_snapshot()` defines the six fields
that make up the optimistic-lock state:

- home_score
- away_score
- home_penalties
- away_penalties
- decided_winner_id
- referee_id

The helper supports both dictionaries and sqlite3.Row.

Match Reporter's quick-save flow and bulk-result preparation now use the same
snapshot definition.

### Real SQLite two-reporter regression
A behavioral test now opens two independent SQLite connections.

1. Both sessions read the same original match.
2. Reporter A saves 2–1.
3. Reporter B attempts to save 0–3 using the stale original snapshot.
4. B's conditional UPDATE returns false.
5. The stored result remains 2–1.

This verifies the actual SQL implementation of
`update_match_result_if_unchanged()` without importing/running Streamlit.

### Referee integrity
A second concurrency test changes referee_id between read and save.
The stale result save is rejected, proving that referee assignment is part of
the protected optimistic-lock state.

## Preserved
- update_match_result_if_unchanged() remains the persistence boundary in app.py
- database transactions remain unchanged
- conflict feedback remains unchanged
- notifications/audit feed happen only for successfully saved updates
- permissions and login behavior are unchanged
- v1.210 sqlite3.Row/public-browser fix and semantic Testmiljö radio E2E fix are included

## Next recommendation
Do not move the conditional UPDATE into a service layer yet. First let v1.211
pass GitHub Actions cross-browser CI. After that, the next safe work item is an
audit of Match Reporter event validation or Initial Tournament Setup.
