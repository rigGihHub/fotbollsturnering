# CupNavi v602 – Full Visual Theme + Access Fix

## P0 bug fix
- Fixes the `Åtkomst & koder` crash when loading pending administrator invitations.
- The pending-invitation read now compares expiry against the database clock with SQLite/Turso `strftime(...)` and binds only the tournament id, avoiding the failing Python datetime parameter path shown in production.
- Invitation creation/revocation behavior is unchanged.

## Full visual theme pass
- Adds a final coherent dark CupNavi shell after historical component styles so old light Streamlit defaults no longer dominate pages.
- Dark navy/near-black background, cyan CupNavi accent, white primary text, muted blue-grey secondary text.
- Restyles sidebar, header, forms, inputs, selects, tabs, expanders, alerts, buttons and generic cards.
- Keeps green for primary/save actions and preserves Text-TV as the strongest visual language in sport-data views.
- Preserves responsive mobile spacing and reduced-motion accessibility.

## Verification
- Python compile/compileall: PASS.
- v602 current release gate: PASS.
- v602 focused regression tests: PASS.
