# v369 – Balanserad Matchcamp-generation från start

- Matchcamp skapar nu en balanserad matchstruktur direkt i stället för full enkelserie.
- Arrangören väljer mål för antal matcher per lag i setupen.
- Standard är 4 matcher per lag.
- CupNavi använder deterministiska round-robin-omgångar och undviker returmöten så länge unika motståndare finns.
- För jämnt antal lag får varje lag exakt målantalet matcher när gruppstorleken tillåter det.
- För udda antal lag fördelas frirond så jämnt som möjligt.
- Målantalet begränsas automatiskt till maximalt antal unika motståndare i gruppen.
- Befintliga matcher tas aldrig bort. Vid komplettering lägger CupNavi bara till unika möten för lag som ännu ligger under målantalet.
- Turnering behåller exakt tidigare beteende: full enkelserie inom gruppen.
- Matchcamp kör inte turneringens hemma/borta-ombalansering efter matchgenerering.
- Ny schemafältmigration v29: `matchcamp_matches_per_team`, default 4.
