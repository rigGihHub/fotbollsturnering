# CupNavi v554 – Tournament Tenant Isolation

## Syfte
Separera arrangörer tekniskt så att ett arrangörskonto bara kan lista och administrera turneringar där kontot har medlemskap.

## Nytt
- Arrangörskonton med e-post + scrypt-hashade lösenord.
- Ny tabell `tournament_members` med per-cup-behörighet och roll.
- Adminens turneringslista filtreras server-side på inloggat konto.
- Direkt guard efter cupval nekar en cup som kontot saknar medlemskap till.
- Nya cuper, klonade upplagor och backup-återställningar kopplas automatiskt till skapande konto som `owner`.
- Det gamla `ADMIN_PASSWORD` finns kvar endast som separat intern **CupNavi driftadmin** och ska inte delas med arrangörer.
- Befintliga cuper utan medlemskap exponeras inte för vanliga arrangörskonton; de kan fortfarande hanteras av driftadmin under övergången.

## Säkerhetsprincip
Det räcker inte att dölja andra cuper i UI. Både listningen och den valda cupen kontrolleras mot `tournament_members` på serversidan.
