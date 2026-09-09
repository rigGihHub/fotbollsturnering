# CupNavi v481 — Turso Failure & Recovery

Version: `2026.09.07-492-BUTTON-LATENCY-III`

- Trasig Turso-sessionanslutning kasseras efter write/commit/read-retry-fel.
- Läsningar får ett enda reconnect-försök.
- Skrivningar och commit retryas aldrig automatiskt.
- Rollback-fel maskerar inte originalfelet.
- Ingen lokal fallback införs.
- Ingen schemaändring.
- Schema v32.
