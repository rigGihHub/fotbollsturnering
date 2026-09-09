# CupNavi v318 – Public statistics fast path

Version: `2026.08.30-318-PUBLIC-STATISTICS-FAST-PATH`

## Finding
The public Topplistor page correctly used one aggregate database query, but that query returned every player with a `player_match_stats` row even when all aggregates relevant to the enabled leaderboards were zero. The Python layer then repeatedly converted aggregate values while filtering/sorting the same rows for goals, assists and cards.

## Change
- Keep one aggregate query; do not split the page into multiple round trips.
- Build the SQL `HAVING` clause from the leaderboards enabled for the tournament.
- Exclude zero-only aggregate rows in the database before Turso/SQLite returns them.
- Use `COALESCE` inside aggregate expressions for stable numeric results.
- Normalize aggregate values and the case-insensitive player sort key once in Python, then reuse them for each enabled leaderboard.
- Keep Skytteliga, Assistliga and Kortstatistik immediately visible when Topplistor is selected.

## Expected effect
Lower result-set transfer and less Python conversion/sorting work on tournaments with many registered players but relatively few goals/assists/cards. There is no extra query and no caching/staleness trade-off.

## Risk
Low. The display rules and tie-break ordering are unchanged; only rows unable to appear in an enabled leaderboard are removed earlier.
