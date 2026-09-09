# CupNavi v470 — Weather, Scorers & Directions

## Varför
Väder och målskyttar fanns kvar men hade blivit för gömda efter performance- och mobilförenklingen.

## Nytt
- `🌦️ Väder för nästa match` visas direkt i Mina lag.
- Knappen öppnar nästa match och aktiverar den befintliga väderprognosen.
- Vädret är fortfarande opt-in/lazy; ingen prognos hämtas på normal first paint.
- `⚽ Målskyttar i senaste matchen` visas direkt under senaste resultat.
- Den öppnar exakt senaste matchen; en deep-linkad match visar redan målskyttar och kort direkt.
- `Nästa för familjen` får en lazy `📍 Vägbeskrivning` till nästa familjematch.
- Befintlig vägbeskrivning för aktivt favoritlag finns kvar.

## Prestanda
Ingen väder-API-trafik på first paint.
Målskyttar hämtas först när en specifik spelad match öppnas.
Vägbeskrivningsdata hämtas först efter uttryckligt toggle-klick.

## Säkerhet
Ingen schema-, resultat-, auth- eller writerlogik ändras.
Schema v32.
