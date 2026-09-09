# CupNavi v463 — Public Match Card Density

## Fokus
Göra matchlistan snabbare att skanna på telefon utan att ta bort kärninformation.

## Förändrat
- Matchkortens mobilpadding och vertikala mellanrum minskas.
- Tid, plan, status, lag och resultat/VS behåller tydlig prioritet.
- `Hemmalag` / `Hemmaställ` tas bort som återkommande lågnyttig text.
- `Bortaställ` visas bara när ett verkligt ställbyte används.
- Matchnummer döljs på mobil men finns kvar på större skärmar.
- Domarrad visas bara när en domare faktiskt är tilldelad.
- Väder visas fortfarande när användaren själv aktiverat väder.

## Prestanda
Ingen ny DB-fråga, ingen ny rerun och ingen ändring i matchfiltrering eller paging.

## Säkerhet
Ingen resultat-, schema-, auth- eller writerlogik ändras.
Schema v32.
