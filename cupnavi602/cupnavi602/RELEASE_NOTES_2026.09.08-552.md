# CupNavi 2026.09.08-552 — Rules-first Admin Flow

- Adds Regler as a dedicated primary admin step.
- Canonical flow is now Cupinfo → Lag → Grupper → Regler → Planer & tider → Schema → Kontroll → Publicera.
- Dedicated rules editor covers match duration, points/tiebreak, playoffs, rest and scheduling principles.
- Rule changes that affect scheduling mark only unplayed schedule rows for re-check and preserve played-match history.
- Simplifies Instructions from a long mixed list to the eight setup steps; secondary features move to an optional-tools area.
- Moves Slutspel detail ownership to Regler; Domare/Funktionärer to Planer & tider; access codes to Cupinfo.
- Keeps referee assignment optional and non-blocking.
- Current release gate: 303 evergreen tests + 26 current/recent contracts passed.
