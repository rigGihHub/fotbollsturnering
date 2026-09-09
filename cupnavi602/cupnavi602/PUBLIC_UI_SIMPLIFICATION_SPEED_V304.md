# CupNavi v1.304 – Public UI simplification & speed

## Goal
Make the primary public Matches journey calmer and cheaper to rerun without changing tournament, schedule, result, auth or persistence behavior.

## Changes
- Reduced the Matches overview to three already-loaded facts: teams, played matches and score total.
- Removed leaderboard highlight cards from the Matches overview. Leaderboards remain available on the Statistics surface.
- Removed the active-visitor metric from the primary match journey.
- As a result, the Matches fragment no longer calls the secondary overview DB snapshot or recalculates all group tables merely to render overview highlights.
- Preserved historical performance profiler keys with zero values so performance history remains comparable.
- Moved the optional weather toggle into the collapsed `Filter & visning` panel together with advanced filters.
- Removed explanatory filter copy that repeated what the controls already communicate.

## Expected effect
- One secondary overview DB snapshot is avoided on every public Matches fragment rerun.
- Full public table/highlight calculations are avoided on every public Matches fragment rerun.
- The top of the Matches page is materially less dense, especially on mobile.
- Weather remains opt-in and is fetched only when explicitly enabled.

## Non-goals
No database schema, scheduler, result handling, publication, authentication, concurrency/CAS or match-event persistence changes.
