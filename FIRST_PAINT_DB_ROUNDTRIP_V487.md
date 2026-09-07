# CupNavi v487 — First Paint & DB Roundtrip Attack

## Fokus
Kapa arbete före första användbara skärmen, framför allt i publik Cupinfo och Cupdagen.

## Förbättringar
- Publik `public_core_snapshot()` öppnar inte längre någon DB/Turso-anslutning när vyn inte behöver vare sig matcher eller lag.
- Cupinfo kan därför få första paint utan en tom remote roundtrip.
- Cupdagen laddar nu regler, matcher och valfri lagincheckning via **en gemensam DB-anslutning**.
- Tidigare gjordes dessa tre läsningar via separata helper-anrop/anslutningar.
- Samma SQL-data och samma säkerhetsmodell behålls; endast anslutningsarbetet minskar.

## Oförändrat
- Ingen lokal fallback.
- Ingen ändring av resultatskrivningar eller optimistic locking.
- Ingen schemaändring. Schema v32.
