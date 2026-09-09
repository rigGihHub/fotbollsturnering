# CupNavi v475 — Playoff Dependency Safety

## Risk
Slutspelsmatcher kan använda `winner:<match_id>` och `loser:<match_id>`.
Tidigare kunde en korrigering av ett tidigare slutspelsresultat ändra vilket lag
som löstes in i en senare match, även om den senare matchen redan hade börjat.

## Skydd
- Centralt skydd i `update_match_result_if_unchanged`.
- Kontrollerar alla senare matcher som refererar till vinnare/förlorare från källmatchen.
- Om vinnarsidan ändras blockeras korrigeringen när en beroende match:
  - har startat/live/paus/avslutats,
  - redan har resultat,
  - eller har registrerade spelarhändelser.
- Om den beroende matchen fortfarande är helt orörd tillåts korrigeringen.
- En korrigering som inte ändrar vinnarsidan tillåts.
- Legacy schema-inline-resultat hade egen direkt SQL och har fått samma guard.
- Reporter bulk visar särskild dependency-blockering i stället för att behandla den som vanlig konflikt.

## Omfattning
Ingen schemaändring.
Ingen automatisk omskrivning av deltagare.
Ingen tyst ändring av redan använd slutspelsmatch.
Schema v32.
