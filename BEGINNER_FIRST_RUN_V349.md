# CupNavi v349 – Beginner First Run

## Mål
En helt ny arrangör ska förstå exakt vad som ska göras direkt efter att en cup skapats.

## Förändringar
- En tom, opublicerad cup med 0 lag/0 grupper/0 matcher får en särskild första-gången-vy.
- Första sidan säger att cupen är skapad och förklarar vägen till en färdig cup i fem begripliga steg.
- Enda primära CTA:n är `Lägg till första laget →`.
- Publiceringskontroller visas inte för en helt tom cup.
- `Schema behöver uppdateras` visas inte som statusproblem innan ett schema faktiskt existerar.
- Uppmärksamhetslistan och avancerade översiktsverktyg döljs i första-gången-läget.
- När användaren har börjat lägga till lag återgår översikten till normal administratörsvy.
- Kalenderns BaseWeb-header/presentation/navigation får explicit ljus bakgrund och mörk text för att motverka mörka CSS-block i datumväljaren.

## Säkerhet
Ingen databasmigrering. Ingen ändring av schemaalgoritm, publiceringsvalidering eller befintliga write-paths.
