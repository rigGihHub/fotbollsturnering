# CupNavi v542 – Clean Schedule Decision Center

- Cleans up the Schema page hierarchy so setup state, blockers and the primary decision are separated clearly.
- Replaces the old verbose 5-item readiness grid with a compact 4-metric status strip and progress bar.
- Only unfinished setup items are shown under **Val som måste göras**.
- Every blocking schedule error is now rendered visibly and individually near the top of the page; warnings remain grouped separately.
- Moves the regenerate/repair confirmation into the same **Nästa steg** card as the primary schedule action.
- Removes duplicated warning/success banners that repeated the same state in several places.
- Keeps direct navigation actions to Teams/Groups/Setup when setup is incomplete.
- Preserves imported-schedule repair semantics and played-match protection from v540.
