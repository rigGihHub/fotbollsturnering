# CupNavi v.1.225 – Team Portal Reliability Bundle 2

## 1. Check-in concurrency protection
Team check-in and removal now use an optimistic snapshot of:
- checked_in
- checked_in_at
- checked_in_by

A stale browser cannot silently overwrite a newer check-in state.

## 2. Kit confirmation protects the version actually shown
Confirmation now verifies the rendered kit colors/patterns and existing
confirmation state before saving. If the kit changed meanwhile, confirmation is
rejected and the latest version reloads.

Already-confirmed kits no longer create repeated confirmation writes/audit
entries from another button press.

## 3. Message sender/recipient integrity
`_send_team_message()` now validates on the server that:
- sender/recipient types are valid;
- sender team belongs to the tournament;
- recipient team belongs to the tournament;
- a team cannot message itself;
- subject/message are non-empty;
- subject is <= 200 chars and message <= 3000 chars.

The UI subject limits now match the server contract.

## 4. Database-level duplicate-submit protection
`team_messages` gains `request_token` with a unique
(tournament_id, request_token) index.

Team, Admin compose and Admin reply forms pass a stable action token. Replaying
the same submit returns the original message instead of inserting a duplicate.
The same token cannot be reused for a different payload.

Notification email is sent only for the first successful insert, so an
idempotent replay cannot send a duplicate email.

## 5. Sent-message notification status
The team portal's Sent view shows whether the email notification was:
- sent;
- failed;
- skipped because no responsible email exists;
- still pending.

## Preserved
No scheduling, results, player/match-roster concurrency, public rendering,
permissions or E2E creation/setup behavior is changed.
