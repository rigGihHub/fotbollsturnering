# CupNavi v486 — Extreme Latency II

Version: `2026.09.07-492-BUTTON-LATENCY-III`

- Reporter explicit reruns: 13 → 3.
- Cupday start-match uses callback; app explicit reruns 90 → 89.
- Undo, recovery-clear and referee acknowledgement use callbacks.
- Successful bulk result autosave no longer triggers an extra rerun.
- Bulk result editor is truly lazy and avoids unnecessary team query/dataframe work.
- Existing write safety and recovery behavior preserved.
- No schema change; schema v32.
