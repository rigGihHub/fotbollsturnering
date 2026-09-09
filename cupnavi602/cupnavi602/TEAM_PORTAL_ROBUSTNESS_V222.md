# CupNavi v.1.222 – Team Portal Roster Concurrency

## Risk addressed
Match squads were saved with DELETE + INSERT using no stale-state check. Two team
leaders, or an admin and a team leader, could therefore silently overwrite each
other's more recent squad selection.

## Fix
Match-roster persistence now uses `_save_match_roster_if_unchanged()`.

The writer:
- begins a transaction before reading the current roster;
- compares the persisted player-id set with the snapshot rendered to the user;
- rejects stale saves instead of overwriting newer data;
- validates that every submitted player still belongs to the team;
- replaces the roster atomically only after those checks pass.

The same protection is used by:
- team portal → Save match squad;
- team portal → Copy previous match squad;
- Admin → Save match squad.

## Behavior on conflict
The stale browser receives a warning and the page reruns with the newest roster.
No newer selection is silently lost.

## Verification
Real SQLite tests simulate stale and fresh roster saves and verify cross-team
player IDs are rejected.

No permissions, squad deadlines, result logic, E2E creation/setup, messaging or
database schema is changed.
