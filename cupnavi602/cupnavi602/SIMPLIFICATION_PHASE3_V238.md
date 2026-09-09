# CupNavi v.1.238 – Simplification Phase 3

## Scope
This pass simplifies:
- Lag
- Grupper
- Trupper

No data model, scheduling, permissions, portal logic or persistence contract is removed.

## Lag
The default task is now clearer: choose class, enter team name and add the team.

Secondary information is progressively disclosed:
- **Tävlingsklasser**
- **Fler laguppgifter** — kits, contact person and travel wishes
- **Digital lagincheckning**
- **Lagportal – koder**
- **Lagmeddelanden**
- **Redigera eller ta bort lag**

This removes several always-visible administration blocks from the normal add-team flow.

## Grupper
- duplicate `Grupper` heading removed;
- guidance shortened;
- CupNavi's group recommendation is now a compact caption instead of a large info box;
- redundant "Skapade grupper" text removed because the placement UI already shows the groups;
- group placement remains the main task;
- edit/delete remains collapsed.

## Trupper
The normal flow is now:
1. choose team;
2. add player;
3. review player list.

Secondary tools remain collapsed:
- Lagportal/match-roster rules;
- Admin match-roster editing.

Position now defaults to **Ej angiven** rather than implicitly classifying every new
player as goalkeeper if the user does not touch the field.

## Test contracts
Historical source-string tests were updated where they required headings that were
deliberately replaced by progressive-disclosure labels. Functional assertions remain:
message inbox/reply, check-in, competition classes, portal rules and match-roster logic
are all still present.
