# CupNavi v.1.230 – Admin Reliability Phase 2

## Sponsor integrity
Sponsor edit/delete now use optimistic snapshots. A stale Admin tab cannot overwrite
or delete a sponsor that another Admin changed meanwhile.

## Functionary integrity
Functionary edit/delete gets the same protection. Functionary email is also validated
before update.

## Publication/lifecycle compare-and-set
Publicera, Avpublicera, Markera pågående and Avsluta cup now operate only when the
persisted publication/lifecycle state still matches the state rendered to Admin.

For publish, match publication and tournament-state update are one transaction. If the
tournament state is stale, the match publication writes are rolled back.

## Audit undo
Schedule-move/delay-shift undo is now one transaction:
1. verify the audit row belongs to the tournament, is reversible and not already undone;
2. restore the tournament-scoped match data;
3. mark the audit row undone;
4. commit once.

A stale double-click/second Admin cannot apply the same undo twice.

## Deferred
Sponsor/functionary creation and shift creation are append-only and lower risk. Their
duplicate-submit semantics can be addressed separately if needed.
