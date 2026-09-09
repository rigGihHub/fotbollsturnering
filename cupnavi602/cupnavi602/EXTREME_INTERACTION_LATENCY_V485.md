# CupNavi v485 — Extreme Interaction Latency

Fokus: färre extra Streamlit-reruns på de hetaste cupdagsknapparna.

- Cupdagen: Starta, Paus, Fortsätt och Avsluta använder callbacks.
- Reporter: live-mål, assist, kort och korrigeringar använder callbacks.
- app.py explicita reruns: 94 → 90 jämfört med v484-baslinjen.
- reporter workspace explicita reruns: 18 → 13.
- Ingen databassemantik eller säkerhetskontroll har tagits bort.
- Ingen schemaändring, schema v32.
