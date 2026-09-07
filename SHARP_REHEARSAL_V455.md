# CupNavi v455 – skarpt genrep

Kör detta först efter deploy mot Turso. Använd minst två riktiga mobiler och gärna en tredje session för samtidighetstestet.

## PASS-krav

1. Admin → Kontroll → Skarpt läge har inga tekniska blockerare.
2. Mobil A kan logga in med cupens matchrapportörskod.
3. Mobil B kan öppna samma match i publikvyn.
4. 1–0 med målskytt syns korrekt publikt.
5. Ångra återställer både resultat och målskytt.
6. Två rapportörssessioner som ändrar samma gamla matchläge kan inte tyst skriva över varandra.
7. Kort nätavbrott + återanslutning skapar inte dubbla mål.
8. Matchen kan avslutas och slutresultatet överlever omladdning.
9. En helt ny session/enhet ser samma resultat och händelser från Turso.
10. Tabell/statistik räknas om korrekt.
11. Om cupen har slutspel: rätt gruppplacering går vidare till rätt slutspelsplats.

Alla obligatoriska punkter måste vara gröna samtidigt som den tekniska readiness-kontrollen är grön. Annars är status NO-GO.

## Inte launch-gate i v455

Browser Web Push är inte fullt aktiverat och är därför inte ett krav för första cupen. Publik livevy, Turso-persistens, resultat/händelser, tabell och slutspel är däremot launch-gates.

## Efter PASS

Frys koden. Använd samma deploy/version och Turso-konfiguration på cupdagen. Om kod, schema eller databasinställning ändras efter genrepet ska relevanta delar av genrepet köras igen.
