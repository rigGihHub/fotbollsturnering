# v314 – Public navigation fast shell

## Syfte
Göra huvudnavigationen i den publika turneringsvyn märkbart snabbare att reagera på när besökaren växlar mellan Cupinfo, Schema & resultat, Tabeller, Slutspel och Statistik.

## Rotorsak
Den publika navigationen renderades tidigare först efter `public_core_snapshot()` och hela `render_public_team_follow()`.

Det innebar att ett vanligt menybyte kunde behöva vänta på:
- hämtning av publicerade matcher och lag,
- favoritlagets snapshot,
- tabellberäkning för valt favoritlag,
- möjlig slutspelsresolution,
- och i vissa fall venue-uppslag,

innan den aktiva huvudmenyn ens ritades om.

## Förändring
För normal publik vy renderas nu den lätta publika shellen först:
1. cupens hero,
2. publika styles,
3. huvudnavigationen med aktiv sektion.

Först därefter laddas kärndata och `Följ mitt lag` samt den valda sidans innehåll.

URL-kontraktet (`?cup=...&section=...&team=...`) och den sticky navigationens HTML/CSS är oförändrade.
Informationsskärmens `screen=1`-flöde behåller sitt tidigare beteende och visar inte den vanliga shellen.

## Effekt
Ändringen minskar inte nödvändigtvis total renderingtiden för varje tung sida, men den flyttar huvudmenyn framför det dyra arbetet så att användaren får navigationsrespons betydligt tidigare. Den tar samtidigt bort `Följ mitt lag` från den kritiska vägen innan menyn ritas.

## Risk
Låg. Ingen datamodell, persistence, auth, concurrency, schema-, tabell- eller slutspelslogik har ändrats.
