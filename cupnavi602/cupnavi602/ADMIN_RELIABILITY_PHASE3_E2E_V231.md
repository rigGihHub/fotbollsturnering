# CupNavi v.1.231 – Admin Reliability Phase 3 + E2E Playoff Contract

## E2E playoff failure fixed
The completed-cup E2E fixture created a real A-playoff bracket and a Final match, but
left the tournament's `playoff_format` at its default `Inget slutspel`.

The public UI correctly obeyed the tournament configuration and therefore hid the
seeded bracket. The test then incorrectly expected `FINAL`.

The fixture now explicitly sets:
- `playoff_format='A- och B-slutspel'`
- `playoff_model_confirmed=1`

when it seeds the bracket. The test still requires the real `FINAL` domain content;
nothing was weakened in the browser assertion.

## Admin phase 3
- Offer edit/delete: optimistic stale-state protection.
- Functionary-shift delete: snapshot protection.
- Participant portal-code rotation: compare-and-set against the rendered credential.
- New portal code survives rerun through session-state feedback.
- Trash/restore/permanent-delete: lifecycle and trashed-version guards.
- Referee creation: basic email validation and corrected form branch behavior.

## Deferred
Bulk missing-code rotation remains a separate operation because it needs a per-team
idempotency contract rather than reusing the single-code flow.
