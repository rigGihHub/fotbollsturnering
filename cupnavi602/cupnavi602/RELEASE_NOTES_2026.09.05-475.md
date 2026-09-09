# CupNavi v475 — Playoff Dependency Safety

Version: `2026.09.07-492-BUTTON-LATENCY-III`

- Blockerar farliga uppströms resultatkorrigeringar när en beroende slutspelsmatch redan används.
- Tillåter korrigering om downstream-matchen är helt orörd.
- Tillåter korrigering som inte ändrar vinnarsidan.
- Skydd i central result writer och legacy schedule-inline writer.
- Ingen schemaändring.
- Schema v32.
