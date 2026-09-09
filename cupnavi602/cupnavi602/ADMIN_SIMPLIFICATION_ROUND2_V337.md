# CupNavi v337 – Admin Simplification Round 2

## Syfte
Minska upplevd komplexitet i Admin utan att ta bort funktioner eller ändra datalagring.

## Ändringar
- Huvudnavigation: Översikt, Deltagare, Matcher, Organisation, Mer.
- Kommunikation tas bort som eget huvudområde; sekundära funktioner samlas under Mer.
- Matchhändelser, tabeller och skytteligor ligger kvar men är sekundära under Matcher.
- Adminöversikten visar som standard endast kompakt status, ett rekommenderat nästa steg, verkliga uppmärksamhetspunkter och ett femstegs cupflöde.
- Snabbadmin, detaljerade förberedelser, separat driftstatus, procentprogress, genvägsblock, checklista, statuskort och dubbla schemavarningar tas bort från standardöversikten.
- Fairness, Cup Control Center och avancerad direktredigering finns kvar bakom `Visa fler verktyg på översikten`.
- Ingen databasmodell, write-path, concurrency-kontroll eller publiceringslogik ändras.
