# CupNavi v581 – Revision Import & Playoff Rules

## Nytt

- Ny adminimport för reviderad PDF/foto efter att cupen redan skapats.
- CupNavi jämför uttryckliga gruppspelsregler, slutspelsregler och plantider mot aktuell setup.
- Administratören väljer exakt vilka ändringar som ska användas.
- Ett befintligt schema skrivs aldrig om automatiskt; ändringar markerar schemat för ny kontroll och avpublicerar opublicerade schemadelar.
- Reviderat matchprogram kan skickas vidare till Schema för separat granskning.
- Slutspel kan nu ha egna halvlekar/perioder, minuter per del, paus och planpaus, med fallback till gruppspelets regler.
- AI-importen skiljer på gruppspel och slutspel och kan läsa uttryckliga planfönster.
- Tröj setup visar hemma/borta sida vid sida. Verifieringsstatus visas endast i adminflödet, aldrig publikt.

## Säkerhet

- Efter registrerade resultat visar CupNavi reviderade regler men blockerar massändring av spelregler/plantider i skarp miljö för att skydda historiken.
- Ingen AI-avläst ändring sparas utan administratörens uttryckliga val.
- Osäkra/omatchade plantider lämnas för manuell kontroll.

## Databas

- Schema v36: `playoff_halves`, `playoff_minutes_per_half`, `playoff_halftime_minutes`, `playoff_pitch_break_minutes` i `schedule_rules`.
