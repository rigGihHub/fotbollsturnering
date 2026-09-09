# CupNavi v341 – Admin Tool Consolidation

Version: `2026.08.31-341-ADMIN-TOOL-CONSOLIDATION`

## Syfte
Minska antalet mentala destinationer i admin utan att radera mogen funktionalitet.

## Förändringar
- `Kontroller`, `Problem & lösningar` och `Instruktioner` tas bort från den globala `Mer`-navigationen.
- Schema äger nu ingångarna till publiceringskontroll och felsökning via `Kontroll & felsökning`.
- Adminöversikt äger ingången till steg-för-steg-guiden under de redan valfria avancerade verktygen.
- De tre mogna arbetsytorna finns kvar oförändrade bakom de kontextuella ingångarna.
- `Mer` fokuserar på separata lågfrekventa funktioner: Cupverktyg, sponsorer/erbjudanden och besöksstatistik.

## Dataintegritet
Ingen databasmigrering. Inga ändringar i resultat-, schema-, publicerings- eller concurrency-write-paths.

## UX-princip
Problem visas nära arbetsytan där de uppstår. Hjälp visas när arrangören ber om den. Global navigation reserveras för verkliga destinationer.
