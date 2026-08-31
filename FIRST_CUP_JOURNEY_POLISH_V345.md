# CupNavi v345 – First Cup Journey Polish

Version: `2026.08.31-345-FIRST-CUP-JOURNEY-POLISH`

## Syfte
Göra CupNavis rekommenderade nästa steg korrekt för en ny cup, inte bara snabbt.

## Förändringar
- CupNavi rekommenderar inte längre **Grupper** efter första laget om cupen har ett planerat/maximalt antal lag som ännu inte uppnåtts.
- Nästa steg visar nu progress, exempelvis `Lägg till lag (5/16)`.
- CupNavi rekommenderar inte **Schema** så länge något registrerat lag saknar grupp.
- Grupper-vyn visar hur många lag som återstår att placera och förklarar att Schema kommer först när gruppindelningen är komplett.
- Ingen databasmigrering och inga write-paths har ändrats.

## Effekt
En ny arrangör leds inte längre vidare för tidigt. Flödet blir: planerat antal lag klart → grupper skapade → alla lag placerade → schema.
