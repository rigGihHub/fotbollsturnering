# CupNavi v454 – Cupday result safety

## Varför
Sista go-live-auditen hittade att schemavyns bekväma resultattabell hade en äldre direkt SQL-väg. Den kunde kringgå både samtidighetsskyddet och v452:s kontroll mot registrerade målskyttsmål.

## Ändrat
- Resultatredigering i Schema använder nu renderad resultatsnapshot för stale-write-skydd.
- En senare ändring från rapportör/admin skrivs aldrig över tyst från en gammal schemavy.
- Samma målskytts-integritetskontroll som i övriga resultatvägar körs före sparning.
- Publiceringsflaggan bevaras som tidigare för säkert sparade matcher.
- UI visar separat antal sparade, konflikter och integritetsblockerade matcher.
- Ingen databasmigration; schema v32 kvarstår.

## Go-live-bedömning
Efter v454 finns ingen känd huvudsaklig admin/rapportörsväg för matchresultat som avsiktligt får skriva lägre resultat än lagrade målskyttsmål eller tyst skriva över ett nyare score-snapshot.
