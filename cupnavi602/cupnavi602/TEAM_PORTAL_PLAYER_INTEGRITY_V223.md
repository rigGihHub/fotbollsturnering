# CupNavi v.1.223 – Team Portal Player Roster Integrity

## Risks fixed
- Two stale team-portal sessions could both pass the UI roster-length check and exceed the configured maximum.
- A stale editor could overwrite a newer player edit.
- A stale page could delete a player that another user had just changed.

## Changes
- Player insertion enforces `max_roster_size` inside the INSERT using the current database count.
- Player edits use an optimistic snapshot of name, first/last name, number, birth year, position and protected status.
- Player deletion uses the same optimistic snapshot.
- Conflicting stale edits/deletes are rejected and the latest data is reloaded.

## Verification
Real SQLite tests cover atomic capacity, stale edit rejection, stale delete rejection and fresh delete.

Admin's existing unrestricted player-add semantics are deliberately unchanged; the configured roster maximum continues to govern the team portal itself.
