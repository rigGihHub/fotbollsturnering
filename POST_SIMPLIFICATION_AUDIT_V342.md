# CupNavi v342 – Post-Simplification Audit

Efter v337–v341 gjordes ett nytt helhetsvarv av adminnavigationen.

## Slutsats
Den kvarvarande gruppen `Mer` hade inte längre en sammanhållen mental modell. Dess fyra synliga destinationer hörde naturligare hemma i befintliga arbetsytor.

## Ändring
- Den tomma legacy-gruppen `Mer` renderas inte längre i huvudnavigationen.
- `Cupverktyg` nås från Schema → Kontroll & felsökning och ägs navigationsmässigt av Matcher.
- `Sponsorer` och `Erbjudanden` nås från Funktionärer → Partners & erbjudanden och ägs av Organisation.
- `Besöksstatistik` nås från Översikt → Visa fler verktyg.
- Kontroller, Problem & lösningar och Guide behåller v341:s kontextuella ingångar.
- Alla bakomliggande arbetsytor finns kvar. Ingen databas- eller write-path har tagits bort.

## Resultat
Global adminnavigation består nu av fyra verkliga arbetsområden:
Översikt · Deltagare · Matcher · Organisation.
