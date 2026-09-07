# CupNavi v491 — Cupday Action Queue

## Syfte
Samla Cupdagens viktigaste operativa signaler i en enda prioriterad kö.

## Prioritet
1. Saknat resultat efter avslutad match
2. Match vars starttid passerat men ännu inte startats
3. Lag/domare som saknas inför nära avspark
4. Kritisk schema-/vilorisk
5. Förseningsrisk och övrigt beslutsstöd

Kön byggs helt från redan laddad Cupday-snapshot, readiness och Autopilot. Inga nya DB-anrop eller API-anrop.

Direktåtgärder: rapportera resultat, starta match, kontrollera lagincheckning, bemanna domare, jämför förseningslösningar eller granska schema.

Ingen automatisk mutation görs utan användarens knapptryck. Schema v32.
