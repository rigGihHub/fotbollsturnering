# CupNavi v336 – Reporter Match Queue

## Förändring
CupNavi Score prioriterar nu rapportörens arbetskö utan att gömma historiska matcher.

- Orapporterade matcher visas först, i ordinarie kronologisk ordning.
- Första orapporterade matchen markeras `▶ Nästa`.
- Övriga orapporterade matcher markeras `○ Orapporterad`.
- Matcher med komplett sparat resultat markeras `✓ Rapporterad`.
- Första orapporterade matchen väljs automatiskt första gången arbetsytan öppnas.
- En kompakt köstatus visar antal orapporterade respektive rapporterade matcher.
- Om alla spelbara matcher är rapporterade visas en tydlig klarstatus, men samtliga matcher kan fortfarande öppnas för livehändelser eller korrigering.

## Integritet
Matchkön är en presentations- och navigationsförändring. Den utför inga databaswrites och ändrar inte resultat-, event-, undo- eller optimistic-locking-logik.
