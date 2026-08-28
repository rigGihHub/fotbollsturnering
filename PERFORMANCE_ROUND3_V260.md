# CupNavi v1.260 – Performance round 3

## Fokus

Minska latens efter navigation och knapptryckningar utan långlivad cache eller svagare concurrency-skydd.

## Ändringar

- Adminöversiktens flödesstatus och dashboardräknare hämtas i samma DB-roundtrip och återanvänds i resten av renderingen.
- Driftstatus (kommande matcher, saknade resultat, kraftigt försenade) räknas i SQL i samma snapshot i stället för att hämta alla matchrader och iterera i Python.
- Antal planer ingår i samma snapshot.
- Instruktionssidan återanvänder ett samlat snapshot för schemalagda/publicerade matcher och matchhändelser i stället för tre extra DB-anrop.
- Publiceringssidans schedule-rules-snapshot innehåller även antal schemalagda matcher. Sekundära adminsidor behöver därför inget extra anrop och får korrekt publiceringsstatus.
- validate_schedule laddar samtliga lag i en batch i stället för ett separat team()-anrop per unikt lag.

Ingen långlivad cache har införts. Skrivningar och optimistic concurrency lämnas oförändrade.
