# CupNavi v492 — Button Latency III

Tre vanliga flöden använder callback-first i stället för knappens normala rerun plus ett extra `st.rerun()`.

- Cupdagen → Jämför lösningar
- Cupinställningar → Ändra cupens inställningar
- Lag → Öppna lagets trupp

`app.py` explicit `st.rerun()` minskar 89 → 86. Ingen DB- eller schemaändring. Schema v32.
