# CupNavi v.1.241 – Simplification Phase 6

## Scope
This pass simplifies:
- Matchhändelser
- Slutspel
- Tabeller

No event-writing, playoff-generation or table-calculation logic was removed.

## Matchhändelser
The page now goes directly from match selection to player-event registration.
The duplicated instructional heading was removed and autosave is stated once at page level.

Secondary validation is shown only when relevant under **Kontroll av mål & assist**.
A non-blocking goal discrepancy is reduced to a short contextual note, while true validation
errors still remain visible and still prevent invalid autosave.

Preserved:
- goal/assist validation;
- card statistics;
- feature flags for assists/cards;
- optimistic concurrency via `update_player_match_stats_if_unchanged()`;
- automatic save and conflict feedback.

## Slutspel
The bracket tree is now the primary content. The previous match-list table is preserved under
**Matchlista** for each bracket.

The playoff model is shown as compact context instead of a large information box. Setup errors,
duplicate-bracket warnings and missing-playoff states remain visible.

## Tabeller
Group tables remain the primary content. Tie-break explanations are no longer repeated below
every group; one collapsed **Så sorteras tabellen** section explains the active rule.

Optional **Slutlig ranking** is collapsed until needed. Its calculation and completion guard are
unchanged.

## Verification intent
The release adds source contracts confirming that the primary content precedes secondary detail
and that match-event concurrency/autosave protections remain intact.
