# CupNavi v319 – Public Playoff Fast Path

Version: `2026.08.30-319-PUBLIC-PLAYOFF-FAST-PATH`

## Goal
Reduce database work when visitors open the public Playoffs page without changing bracket generation, match resolution or playoff rules.

## Change
The public page now reads existing brackets first. If a bracket already exists, it is treated as the display source of truth and `playoff_specs_for_tournament()` is not called. Setup validation is only evaluated when no bracket exists and the page needs to explain why.

For the A/B playoff model this avoids the group lookup and team-count aggregation on ordinary public playoff reruns. The existing bracket query, duplicate detection, bracket rendering and lazy forecast remain unchanged.

## Behaviour preserved
- Existing brackets render exactly as before.
- Missing bracket warnings still distinguish invalid setup, valid-but-not-generated setup and no tree.
- Duplicate bracket warning remains.
- No changes to schedule generation, source resolution, results, tie-breaks or concurrency.
