# CupNavi v486 — Extreme Latency II

## Fokus
Minska upplevd knappfördröjning och onödigt arbete i cupdagens hetaste flöden.

## Förbättringar
- Reporterlägets explicita `st.rerun()` minskade från 13 till 3.
- Ångra senaste händelse körs i callback och använder bara widgetens normala rerun.
- Återställningsmeddelandets klar-knapp körs i callback.
- Domarbekräftelse körs i callback.
- Lyckad massinmatning av resultat tvingar inte längre en extra rerun.
- Avancerad massinmatning är nu verkligt lazy:
  - ingen extra lagquery,
  - ingen dataframe-byggnad,
  - ingen tung data_editor
  förrän användaren öppnar funktionen.
- Cupdagens “Starta match” använder samma status-callback som övriga snabba statusknappar.

## Säkerhet
- Optimistic locking och konfliktkontroller är oförändrade.
- Fel vid osäkra writes behåller recovery-flödet från v482/v483.
- Ingen schemaändring. Schema v32.
