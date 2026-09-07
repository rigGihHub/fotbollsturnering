# CupNavi v459 — Mobile Flow Friction Audit

## Fokus
Minska scroll och informationsfriktion i verkliga telefonflöden utan ny backendlogik.

## Förändrat i Lagportalen
- Cupdagsstatusen visar fortfarande progression och nästa konkreta steg direkt.
- Den fulla checklistan ligger nu bakom `Visa hela checklistan` i stället för att alltid ta stor höjd före huvudflikarna.
- `Mina matcher` visar i första hand de tre närmast kommande matcherna.
- Om cupdagen redan är avslutad visas de tre senaste matcherna.
- Hela matchlistan finns fortfarande ett tryck bort via `Visa alla X matcher`.

## Varför
På 360–430 px skärmar var användaren tidigare tvungen att skrolla förbi flera readiness-rader och potentiellt en lång matchlista för att komma vidare till kontakt, trupp och andra uppgifter. v459 använder progressiv fördjupning: viktigast först, allt finns kvar.

## Säkerhet
- Ingen DB-fråga tillkommer.
- Ingen writer, auth-, resultat-, schema- eller samtidighetslogik ändras.
- Ingen schemaändring; schema v32.
