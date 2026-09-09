# v1.251 – Domar- och matchrapportörskoder

- Admin → Domare visar nu **Åtkomstkoder** med **Matchrapportör** och **Domare** sida vid sida på samma nivå.
- Båda använder separata fyrsiffriga, turneringsspecifika koder.
- Båda lagras saltat/hashat och kan roteras oberoende.
- En domarkod kan användas i samma snabba rapporteringsinloggning men sessionen markeras uttryckligen som domarroll.
- Kodrotation ogiltigförklarar den gamla kodens aktiva sessioner.
