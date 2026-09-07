# CupNavi v471 — Smart Match Cards

## Målskyttar
- När matchhändelser är laddade visas de kompakt direkt i matchkortet.
- Om endast mål finns heter sektionen `Målskyttar`.
- Om mål och röda kort finns heter den `Målskyttar & kort`.
- Befintlig lazy event-loading behålls, så inga nya eventfrågor på first paint.

## Väder
- Matcher som startar inom 180 minuter får ett direkt snabbval `🌦️ Visa väder`.
- Användaren behöver inte gå tillbaka till filterpanelen.
- Prognosen hämtas fortfarande först efter aktivt knapptryck.
- Den befintliga väderraden i matchkortet återanvänds.

## Prestanda
Ingen vädertrafik utan användarens val.
Ingen ny eventfråga utan event-toggle eller exakt matchlänk.
Ingen schemaändring.

Schema v32.
