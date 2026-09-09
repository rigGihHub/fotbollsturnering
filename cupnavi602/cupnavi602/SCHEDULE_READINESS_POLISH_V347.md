# CupNavi v347 – Schedule Readiness Polish

Version: `2026.08.31-347-SCHEDULE-READINESS-POLISH`

## Syfte
Göra sista steget in i schemagenereringen tydligt och säkert. CupNavi ska inte signalera att schemat kan skapas när deltagarlistan fortfarande är ofullständig.

## Förändringar
- Schemagenereringen kontrollerar nu även planerat antal lag (`expected_team_count`).
- En kompakt förkontroll visar fem grundkrav:
  1. Deltagarlista
  2. Grupper
  3. Gruppplacering
  4. Gruppstorlek
  5. Slutspelsmodell
- Progress visas som antal klara steg.
- När alla fem är klara visas en tydlig `Redo att skapa spelschema`-signal.
- Om planerade lag saknas blockeras generering med konkret status, exempelvis `registrera alla lag (10/16)`.

## Säkerhet
Ingen databasmigrering. Ingen förändring av själva schemaalgoritmen, matchskapandet, publiceringen eller concurrency-skydden.
