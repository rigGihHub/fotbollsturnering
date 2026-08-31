# CupNavi v326 – First Cup Fast Track

## Mål
Minska tiden och antalet steg från nyskapad cup till första publicerbara schema utan att ta bort avancerade inställningar.

## Ändringar
- Setupens minimiväg slutar efter tävlingsklass och plantider. När dessa är giltiga kan arrangören gå direkt till Lag.
- Format, regler, prioriteringar och serviceval ligger kvar i den detaljerade setupen och kan justeras senare.
- Adminöversikten visar en tydlig fyrastegs snabbväg för opublicerade cuper utan spelade matcher: Lag → Grupper → Schema → Publicera.
- Snabbvägen återanvänder befintlig workflow-snapshot och lägger inte till någon DB-query.
- Trupper, domare, sponsorer och andra verktyg finns kvar men blockerar inte grundflödet.

## Dataintegritet
Ingen ändring av resultat, schemaalgoritm, gruppdata, publiceringsvalidering, auth eller concurrency-skydd.
