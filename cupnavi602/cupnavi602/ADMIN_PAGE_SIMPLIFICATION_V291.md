# CupNavi v1.291 – Admin page simplification

## Mål
Fortsätta UI-genomgången från v1.289–v1.290 med fokus på innehållstäthet inne på adminsidorna, utan att ändra cupens domänlogik eller ta bort funktionalitet.

## Förändringar
- Instruktionssidans introduktion kortades och en intern/metateknisk slutcaption togs bort.
- Fairness-hjälptexten kortades till det som arrangören behöver för att tolka poängen.
- Cupinställningar visar nu primär åtgärd och fas först. Sportprofil och formatrekommendation är samlade i en stängd expander: `Tävlingsprofil och rekommendation`.
- Rubriken `Tekniska verktyg` togs bort ovanför den redan självförklarande togglen för teknisk hälsa/backup.
- Introduktionerna för Problem & lösningar, Spelare & trupper, Domare/åtkomstkoder, Import och Cupverktyg kortades.

## Avgränsning
Ingen ändring av databas, schemaalgoritm, resultatlogik, auth, publicering eller concurrency/CAS. Inga funktioner har tagits bort.

## UI-princip
Primär uppgift först. Sekundär besluts- och teknikinfo ska finnas kvar men inte konkurrera visuellt med den vanligaste åtgärden.
