# CupNavi v469 — Family Travel Guidance

## Nytt
- `Nästa för familjen` använder CupNavis befintliga planförflyttningstider när de finns.
- Marginal räknas konservativt från beräknad matchslut, inte från föregående avspark.
- Visar `Planerad förflyttning: X min` och återstående marginal till nästa avspark.
- Samma plan kräver ingen förflyttning.
- Saknad förflyttningstid visas uttryckligen; CupNavi hittar inte på en tid.
- Negativ eller mycket liten marginal klassas som varning.

## Viktig terminologi
Automatiskt beräknade tider i `pitch_travel_times` är körtid plus arrangörens valda buffert.
Därför kallas värdet `planerad förflyttningstid`, inte gångtid.

## Prestanda
Rese-/regeldatan laddas endast när användaren följer flera lag och det faktiskt finns en efterföljande favoritmatch.
Vanlig publik first paint och singelfavorit påverkas inte.

## Säkerhet
Ingen schema-, resultat-, auth- eller writerlogik ändras.
Schema v32.
