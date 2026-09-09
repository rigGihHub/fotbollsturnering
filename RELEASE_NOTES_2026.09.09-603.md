# CupNavi v603 — Global Dark Shell + Access Hotfix

## Scope
- Applies the dark CupNavi sports shell across public, admin, setup and role surfaces.
- Keeps Text-TV styling strongest in tables/results while making forms, tabs, cards, sidebar and controls part of the same visual system.
- Repairs the `tournament_admin_invitations` schema on every startup for mixed/partial Turso deployments.
- Makes the pending-invitations read fail-safe so a stale cloud schema cannot crash the entire `Åtkomst & koder` page.
- Keeps the calendar deliberately light for date legibility.

## Validation
- Python compile: PASS
- Evergreen suite: 302 passed, 2 deselected
- Current semantic release gate: 169 passed
- v603-specific gate: 4 passed
