# v387 – FAST CORE UX

Fokus: snabbare kärnflöde utan nya funktioner.

## Lag
- Fotoimport, fler lagverktyg, digital incheckning, lagkoder, lagmeddelanden och redigera/ta bort lag är nu riktiga lazy-val.
- Tidigare låg flera av dessa i kollapsade expanders, men Streamlit bygger ändå innehållet i en expander. Nu laddas innehållet först när användaren öppnar verktyget.
- Grundflödet för att lägga till lag ligger kvar synligt.

## Schema
- Visuellt schema, drag-and-drop, matchjustering och resultatredigering ligger nu bakom `Visa detaljer och redigering`.
- Den stora matchfrågan för justerbara matcher körs inte innan verktyget öppnas.
- Matchdetaljer och matchhändelser byggs inte för varje match i normal schemavy.
- Detta undviker den dyraste normala detaljrenderingen på schemasidan.

## Resultat
- Resultatvyn öppnar nu som standard `Att rapportera`.
- Endast matcher som saknar resultat byggs i den redigerbara tabellen.
- `Alla matcher` finns kvar när ett tidigare resultat behöver korrigeras.
- Autosave arbetar bara mot de matcher som faktiskt visas i den aktiva redigeringsvyn.

## Oförändrat
- Databasmodell och schema är oförändrade (v30).
- Resultatens optimistiska låsning och autosave är kvar.
- Alla sekundära verktyg är fortfarande åtkomliga.
