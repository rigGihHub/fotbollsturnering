# CupNavi v480 — Production Readiness Audit

## Viktigaste fyndet
CupNavi avgjorde tidigare Turso-läge med:
`bool(TURSO_DATABASE_URL and TURSO_AUTH_TOKEN)`.

Om bara en av hemligheterna var satt blev resultatet falskt och appen kunde gå vidare mot lokal SQLite. Go-live-vyn blockerade senare skarp start, men databasmotorn i sig gjorde ingen skillnad på helt okonfigurerat och halvkonfigurerat Turso.

## v480
- Introducerar `TURSO_CONFIG_PARTIAL`.
- Om exakt en Turso-hemlighet finns vägrar `db()` att använda lokal fallback.
- Felmeddelandet anger vilken hemlighet som saknas.
- Go-live visar separat blockerare för halvkonfigurerat Turso.
- `ADMIN_PASSWORD` är nu också ett uttryckligt GO/NO-GO-krav.
- Komplett Turso + adminskydd visas grönt.

## Externa tjänster
Väder (Open-Meteo) och Google Routes är fortsatt icke-kritiska:
- väderfel ger kontrollerat meddelande,
- Routes-fel stoppar endast restidsberäkningen,
- de får inte blockera cupens kärnflöde.

## Backup
Befintlig backup/restore är kvar:
- portabel JSON,
- SHA-256,
- restore skapar ny cup,
- original skrivs aldrig över.

Ingen schemaändring. Schema v32.
