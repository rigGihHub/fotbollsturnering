# CupNavi v.1.228 – Public View Performance & Query Audit

## Audit
The public shell is already partially decomposed and uses render-level query and derived caches.
The safest remaining gains were in information-screen tables and playoff bracket rendering.

## Changes

### Information screen tables
The screen mode previously called `calculate_table()` once for each displayed group.
Each call can issue two queries (teams + completed group matches).

The screen now calls `calculate_all_group_tables()` once and reuses its batched result.
For four displayed groups this changes the table work from up to 8 group-specific reads
to the existing 3-query batch.

### Playoff bracket team lookups
`render_bracket_tree()` previously called `team(home_id)` and `team(away_id)` for every
match card. The render cache avoided repeated IDs, but a bracket with many distinct teams
could still produce an N+1-style pattern.

The bracket now loads all teams for its tournament once and uses an id lookup map for:
- team colors;
- team names when the source resolves to a team.

Complex winner/loser/group source resolution is deliberately unchanged.

## Preserved
No public filtering, standings rules, playoff resolution, result visibility, routing,
analytics, permissions or E2E creation behavior changes.
