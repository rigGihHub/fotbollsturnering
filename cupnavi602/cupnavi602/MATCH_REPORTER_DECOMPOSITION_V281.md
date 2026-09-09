# CupNavi v1.281 – Match Reporter decomposition

This release continues the strangler-style reduction of `app.py` without moving
optimistic-locking or persistence boundaries.

## Changes

- Added `cupnavi_core/match_reporter_repository.py` for Match Reporter read-only queries:
  scheduled/completed matches, teams, match-roster/player fallback, player-match stats,
  referees, referee assignments and acknowledgement reads.
- Added `cupnavi_core/match_reporter_view.py` for pure event-row projection, feature-driven
  reporter columns, referee assignment labels and offline-draft markup.
- The offline draft JSON now escapes `</...` sequences before embedding user-controlled
  team labels in a `<script>` block, preventing a label such as `</script>` from terminating
  the script early. Option labels continue to be inserted with `textContent`.
- `app.py` delegates these read/presentation responsibilities while retaining all result,
  player-event and referee acknowledgement writes.

## Safety

No schema/data migration. Result/event optimistic locking remains unchanged in `app.py`.
No authentication, authorization, publication or tournament-lifecycle behavior changed.
