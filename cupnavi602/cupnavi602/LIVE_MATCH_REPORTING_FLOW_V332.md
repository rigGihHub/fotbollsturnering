# CupNavi v332 – Live Match Reporting Flow

## Mål
Göra flera matchhändelser i följd snabbare att registrera på mobil utan att ändra persistence- eller concurrency-gränser.

## Ändringar
- Vald match, valt lag och vald spelare fortsätter ligga kvar efter en sparad händelse.
- Två fullbredda touchknappar, **Föregående spelare** och **Nästa spelare**, gör spelarbyte snabbt utan att öppna selectboxen.
- **Senast registrerat** ligger kvar med händelsetyp, tröjnummer, spelarnamn och lag så rapportören direkt kan bekräfta senaste trycket.
- Snabbhändelser fortsätter använda `deps.save_event_rows` och befintlig optimistic locking.
- Mål-/assistvalidering och lazy massinmatning är oförändrade.

## Ingen schemaändring
Ingen databas- eller beroendeändring.
