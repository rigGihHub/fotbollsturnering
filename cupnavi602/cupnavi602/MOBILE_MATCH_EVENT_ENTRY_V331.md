# CupNavi v331 – Mobile Match Event Entry

Version: `2026.08.30-331-MOBILE-MATCH-EVENT-ENTRY`

## Förändringar
- Matchrapportörens Matchhändelser visar ett lag i taget för mindre scroll på telefon.
- Touch-first snabbinmatning är standard: välj spelare och registrera mål, assist, gult eller rött kort med stora knappar.
- Den valda spelarens aktuella händelser visas direkt ovanför knapparna.
- Korrigering av felregistrering finns under en separat, kompakt korrigeringsyta.
- Matchresultatets målgräns valideras även i snabbinmatningen innan någon write görs.
- Befintlig optimistic locking via `save_event_rows` används oförändrat.
- Den fulla tabellen finns kvar bakom `Visa tabell för massinmatning` och renderas bara på begäran.
- Bara det valda laget laddar spelare och matchstatistik, vilket minskar onödiga queries/rendering i Matchhändelser.

## Integritet
Ingen ny databasmodell eller skrivmekanism har införts. Snabbinmatningen skapar samma CAS-skyddade player_match_stats-uppdatering som tidigare tabellflöde.
