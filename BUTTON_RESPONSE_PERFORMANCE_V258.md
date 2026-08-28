# CupNavi v1.258 – Button response performance

## Fokus
Den här releasen gör en riktad prestandarunda på sådant som händer direkt efter vanliga knapptryckningar i Admin. Målet är färre onödiga databasvarv och färre SQL-skrivningar utan att försvaga färsk data, optimistic concurrency eller befintliga säkerhetsspärrar.

## Ändrat
- Globala flödesräknare laddas nu bara på de sju primära cupstegen. Sekundära adminsidor slipper ett onödigt sammansatt COUNT-anrop vid varje rerun/navigation.
- `Spara incheckning` samlar ändrade lag först och skriver både lagstatus och audit-logg i en och samma databastransaktion. Tidigare öppnade audit-loggningen en ny anslutning och commit per ändrat lag.
- `Spara gruppindelning` uppdaterar bara lag vars grupp faktiskt har ändrats och använder batchskrivning.
- `Spara alla resultat i schemat` skriver bara matcher vars resultat faktiskt ändrats. För publicerade cuper kombineras resultat och `schedule_published` i samma UPDATE i stället för två UPDATE per match.
- Synligt versionsnummer i sidomenyn är synkroniserat till v1.258.

## Avgränsning
Ingen långlivad cache har lagts ovanpå cupdata. Det är medvetet: svarstider förbättras utan att skapa risk för stale data mellan administratörer eller externa databasändringar.

## Test
- 259 non-E2E-testfiler passerade i tre batcher.
- Compile: PASS.
- E2E syntax: PASS.
- Browser-E2E körs fortsatt i GitHub Actions.
