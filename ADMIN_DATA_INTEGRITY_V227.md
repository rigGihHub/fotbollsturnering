# CupNavi v.1.227 – Admin Data Integrity & Reliability

## Admin write audit
The Admin area contains 51 direct INSERT/UPDATE/DELETE call sites. This release
does not blindly rewrite all of them. It hardens the highest-risk interactive
writes where a stale browser tab can otherwise overwrite or delete newer data.

## Hardened in v1.227

### Team editing
Admin team edits now use an optimistic snapshot covering:
- team name
- kit colors/patterns
- travel settings
- schedule wishes
- responsible contact
- age/competition class
- group assignment

A stale form cannot overwrite a newer team edit. Admin contact email also gets
the same basic validation used in the team portal.

### Team deletion
Team deletion first verifies that the team still matches the version Admin saw.
The destructive transaction is tournament-scoped, including affected matches
and brackets, so a matching source token in another tournament is untouched.

### Group editing/deletion
Group edits and deletes use optimistic snapshots. A stale Admin page cannot
rename/delete a group that another Admin has changed meanwhile.

Group cleanup is tournament-scoped and unassigns teams only within the same
tournament.

### Schedule-request status
Approve/Reject is now an atomic state transition:
`WHERE id=? AND tournament_id=? AND status=?`.

A stale Godkänn/Neka button cannot reverse a decision made in another Admin
session. Legacy scheduler mirror fields are updated only after a successful
transition and are tournament-scoped.

## Verification
Real SQLite tests cover:
- stale team edit rejection;
- stale team delete rejection;
- tournament-scoped fresh team deletion;
- stale group edit/delete rejection;
- competing schedule-request decisions.

## Deferred from the audit
Bulk generators, explicit resets, publishing lifecycle transitions, sponsor and
functionary maintenance, and audit undo remain separate risk domains. They
should be hardened in follow-up passes rather than folded into one large
refactor.
