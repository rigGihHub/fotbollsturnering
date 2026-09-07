# CupNavi v458 — Interaction Latency Audit

Version: `2026.09.07-492-BUTTON-LATENCY-III`

- Reducerar explicita full-reruns i `app.py` från 102 till 94.
- Språkbyte och admin-entry-navigation använder single-rerun callbacks.
- Ny rapportörs-/domarkod visas utan en extra full appkörning.
- Resultat-, schema-, auth- och samtidighetsflöden lämnas medvetet orörda.
- Ingen schemaändring; fortsatt schema v32.
- v456 är fortsatt fryst go-live-kandidat tills skarpt genrep är genomfört.
