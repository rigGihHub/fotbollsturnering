# CupNavi v461 — Cupday Mobile Admin Density

## Fokus
Arrangörens mobilvy ska svara på fyra frågor direkt:
1. Vad pågår nu?
2. Finns ett problem?
3. Vad händer härnäst?
4. Vad ska jag göra?

## Förändrat
- Operativ puls flyttas direkt under CupNavis primära rekommendation.
- Tre kompakta tal visas först: `Pågår nu`, `Problem`, `Nästa 45 min`.
- Cupdagsprogress visas direkt under pulsen.
- Inför nästa avspark visar bara den viktigaste beredskapsrisken öppet.
- Övriga beredskapspunkter finns bakom en expander.
- Planöversikten ligger bakom `Planer just nu · X` i stället för att alltid fylla skärmen.
- Den gamla dubbla KPI-raden längre ned tas bort.

## Säkerhet
Ingen DB-fråga, writer, matchstatuslogik, schemaalgoritm eller resultatlogik ändras.
Schema v32.
