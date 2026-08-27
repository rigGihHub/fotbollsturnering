# CupNavi v.1.212 – Match Events Hardening

## Implemented
- Extracted Matchhändelser change detection/normalization to pure `cupnavi_core.match_event_logic`.
- Handles empty/NaN editor values safely as zero instead of relying on Python truthiness.
- Writes only actually changed player rows.
- Each prepared change carries the previously loaded event counters as an `expected` snapshot, preparing the next concurrency-hardening step.
- Existing validation still blocks autosave when player goals/assists exceed the match result.
- Existing database UPSERT semantics are deliberately unchanged in this release.

## Regression coverage
Tests cover:
- NaN/empty editor values;
- unchanged rows produce no write;
- changed rows carry new values plus expected snapshot;
- first-time player statistics start from a zero snapshot.

## Important remaining risk
`player_match_stats` still uses UPSERT without optimistic locking. Two simultaneous event reporters can therefore theoretically overwrite each other's player-stat changes. v1.212 does not pretend this is solved. The expected snapshot added here creates the safe basis for implementing and testing conditional event writes in the next phase.
