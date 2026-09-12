# CupNavi v652 — återställd API-koppling

- Stoppar ogiltiga eller platshållarbaserade API-adresser i produktionsbygget.
- Använder CupNavis riktiga Render-API som säker produktionsreserv.
- Behåller localhost som reserv endast under lokal utveckling.
- Centraliserar API-adressen för samtliga klientbaserade adminmoduler.
- Behåller autentisering och serverbaserad behörighetskontroll intakt.

Rättningen löser `API-fel 404` på admininloggningen utan att göra adminpanelen publik.
