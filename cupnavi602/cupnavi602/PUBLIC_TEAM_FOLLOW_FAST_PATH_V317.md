# CupNavi v317 – Public Team Follow Fast Path

## Problem
Med ett favoritlag valt gjorde den publika vyn extra DB-arbete på varje Streamlit-rerun: `calculate_table()` hämtade lag och färdigspelade gruppmatcher igen för tabellpositionen, och nästa plans vägbeskrivning slog mot `venue_points` även när länken inte användes.

## Ändring
- Tabellpositionen räknas nu från den redan laddade publika lag- och match-snapshoten med samma `calculate_group_table`-semantik.
- Nästa match och tabellposition är fortsatt direkt synliga.
- Vägbeskrivning hämtas först när användaren aktiverar `📍 Visa vägbeskrivning till nästa match`.
- Prenumeration och notishistorik är oförändrade; notishistoriken är fortsatt lazy enligt v312.

## Effekt
När ett lag följs försvinner två DB-frågor per rerun för tabellpositionen och normalt ytterligare en venue-fråga tills vägbeskrivningen faktiskt efterfrågas. Det minskar kostnaden vid byte mellan Cupinfo, Schema, Tabeller, Slutspel och Statistik utan att gömma nästa match eller tabellposition.
