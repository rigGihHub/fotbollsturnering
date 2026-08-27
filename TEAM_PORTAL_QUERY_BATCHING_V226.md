# CupNavi v.1.226 – Team Portal Query Batching

## Improvements
- The team inbox is fetched once and reused for both unread count and inbox display.
- All match-roster rows for the logged-in team are fetched in one query.
- Current match squad, matches with registered squads, and Copy previous squad
  reuse the same in-memory roster map.
- Match and player labels use id maps rather than repeated linear scans.

## Impact
A normal Lagportal render removes two redundant reads:
- unread COUNT + inbox fetch becomes one inbox fetch;
- selected squad + DISTINCT rostered matches becomes one batched roster fetch.

Copy previous match squad avoids another read when used.

No write semantics, permissions, deadlines, concurrency protection or E2E/setup
behavior changes.
