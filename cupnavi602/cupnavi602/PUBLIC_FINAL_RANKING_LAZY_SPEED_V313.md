# v313 – Public final ranking lazy speed

Version: `2026.08.30-313-PUBLIC-FINAL-RANKING-LAZY-SPEED`

## Audit finding

The public **Tabeller** page calculated `final_ranking_rows(...)` on every rerun whenever final ranking was enabled, even while the tournament was still in progress. The result cannot be shown until every published match is completed, so the work was discarded during active tournaments.

`final_ranking_rows(...)` can trigger extra work for teams, all group tables, playoff matches, source resolution and competition classes.

## Change

CupNavi now checks whether every published match is completed **before** calculating final ranking. During an active tournament the existing explanatory caption is shown without building the ranking.

When all published matches are finished, ranking behavior is unchanged.

## Risk

Low. The visibility condition is unchanged; only the order of the existing completion check and ranking calculation changed.
