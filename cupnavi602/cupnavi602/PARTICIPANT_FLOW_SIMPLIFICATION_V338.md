# v338 – Participant Flow Simplification

Version: `2026.08.31-339-MATCH-WORKSPACE-SIMPLIFICATION`

## Syfte
Minska antalet mentala destinationer under Deltagare utan att ta bort funktionalitet eller ändra persistenslogik.

## Ändringar
- Deltagare visar nu endast **Lag** och **Grupper** i den globala adminnavigationen.
- **Spelare & trupper**, **Schemakrav & önskemål** och **Import** finns kvar som kontextuella **Fler lagverktyg** från Lag.
- Dolda lagverktyg mappas fortfarande till adminområdet Deltagare så navigationen inte hoppar till Översikt.
- Rubriker/hjälptexter markerar att dessa sidor är lagverktyg.
- Befintliga write-paths, tabeller, importlogik, rosterlogik, önskemålslogik och concurrency-skydd är oförändrade.

## Avgränsning
Ingen databas- eller schemamigration. Ingen ny dependency. Ingen funktion tas bort.
