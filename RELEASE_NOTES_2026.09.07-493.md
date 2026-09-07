# CupNavi v493 — Button Latency IV

Version: `2026.09.07-493-BUTTON-LATENCY-IV`

- Reduced explicit `st.rerun()` calls in `app.py` from 86 to 77.
- Converted nine pure UI/navigation/confirmation flows to callback-first state changes.
- Focus areas: team setup navigation, max-team/class navigation, team-code confirmations, and offer-delete confirmation.
- No intentional changes to database schema, result rules, match integrity, playoff integrity, or transaction safety.
