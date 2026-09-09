# CupNavi v435 – Admin navigation fast path

Fokus: kapa onödiga remote DB-varv i Admin → Lag → Grupper → Trupper utan att göra sparad data stale.

- Lag-sidan kör inte längre den muterande `sync_competition_classes()` på varje vanlig render. Synk sker när klassinställningar faktiskt ändras; endast tom legacy-data repareras i Lag-vyn.
- Korta cross-rerun snapshots för lag (8 s), grupper (8 s) och tävlingsklasser (12 s) gör snabba flikbyten och widget-reruns betydligt billigare.
- Alla `run()`-skrivningar invalidates admin-snapshots direkt, så en sparad ändring visas färsk på nästa render – ingen väntan på TTL.
- Befintlig render-cache ligger kvar som första nivå; denna release minskar framför allt latency från Turso mellan Streamlit-reruns.

Produktprincip: navigation ska vara read-only. Vi ska inte göra migrations-/synk-UPDATEs bara för att användaren öppnar en sida.
