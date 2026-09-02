# v388 – ADMIN CORE FLOW CLEANUP

Fokus: kortare kärnflöde och färre onödiga databasläsningar.

## Grupper
- Manuell gruppskapning är nu ett riktigt lazy-val: `Skapa grupper själv`.
- Redigera/ta bort grupp är också lazy.
- CupNavis rekommenderade gruppväg ligger kvar som huvudväg.
- Två extra readiness-frågor till databasen har tagits bort. Redan laddade `teams` och `groups` används för att avgöra om alla lag är placerade.
- Hjälptexten för oplacerade lag är kortare.

## Resultat
- Resultatsidan laddar matchlistan först.
- Domare och laglista hämtas först om det faktiskt finns matcher med två klara lag som kan rapporteras.
- Detta sparar två DB-anrop i tomma/ej redo resultatlägen.
- Standardvyn `Att rapportera` från v387 är kvar.

## UX-princip
- Rekommenderad huvudväg synlig.
- Manuella eller destruktiva verktyg sekundära och lazy.
- Ingen funktion har tagits bort.

## Oförändrat
- Databasschema v30.
- Resultatens autosave och optimistic locking kvar.
