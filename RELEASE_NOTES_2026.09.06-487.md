# CupNavi v487 — First Paint & DB Roundtrip Attack

Version: `2026.09.07-492-BUTTON-LATENCY-III`

- Cupinfo first paint avoids opening Turso when neither matches nor teams are requested.
- Cupdagen batches rules + matches + optional team check-ins through one DB connection.
- No feature additions.
- Write safety unchanged.
- No schema change; schema v32.
