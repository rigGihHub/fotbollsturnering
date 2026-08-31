# CupNavi v346 – First Cup Smart Progress

Version: `2026.08.31-346-FIRST-CUP-SMART-PROGRESS`

## Syfte
Göra övergången Lag → Grupper → Schema självklar och hindra CupNavi från att föreslå automation på ofullständig deltagardata.

## Förändringar
- Lag visar faktisk registreringsprogress när planerat/max antal lag är känt.
- När deltagarlistan är komplett visas en tydlig primär CTA: `Fortsätt till Grupper`.
- Grupper känner av om deltagarlistan fortfarande är ofullständig och leder tillbaka till Lag.
- Smart gruppindelning och rekommenderad automatisk gruppskapning väntar tills deltagarlistan är komplett.
- Gruppvyn visar placeringsprogress.
- När alla lag har en grupp visas `Fortsätt till Schema`.

## Säkerhet
Ingen databasmigrering och inga förändringar i befintliga write-paths, schemaalgoritm eller concurrency-skydd.
