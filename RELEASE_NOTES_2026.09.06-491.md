# CupNavi v491 — Cupday Action Queue

Version: `2026.09.07-492-BUTTON-LATENCY-III`

- Adds deterministic read-only operational action queue to Cupdagen.
- Reuses existing snapshot/readiness/autopilot data; zero new DB/API calls.
- Prioritizes missing results and overdue starts above secondary risks.
- Provides direct one-click handoff/actions with existing safe callbacks.
- No schema change; schema v32.
