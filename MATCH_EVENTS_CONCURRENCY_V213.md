# CupNavi v.1.213 – Match Events Concurrency

## Problem
User-facing Matchhändelser used unconditional UPSERTs. Two browser sessions could
therefore overwrite each other's newer player-event counters without warning.

## Fix
`update_player_match_stats_if_unchanged()` adds optimistic locking to one player's
match-event counters using the expected snapshot prepared in v1.212.

The conditional write protects:
- goals
- assists
- yellow cards
- red cards

It is now used in both:
- Matchrapportör → Matchhändelser
- Admin → Matchhändelser

## Real concurrency tests
Two independent SQLite connections simulate two reporters:
1. Both start from the same player-event snapshot.
2. Reporter A saves.
3. Reporter B saves from stale state.
4. B is rejected and A's values remain stored.

A separate test covers the first-insert race where neither session initially had
a player_match_stats row.

## UX
Conflicted player rows are not overwritten. The user receives a warning and the
view reruns to load the newest persisted values.

## Deliberately unchanged
Demo-data generation keeps its unrestricted UPSERT because it is not a
simultaneous interactive reporting flow.
