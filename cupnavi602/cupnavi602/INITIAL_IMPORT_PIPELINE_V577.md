# Initial import pipeline v577

Målet är att en arrangör ska kunna fotografera ett befintligt cupprogram en gång i början och sedan återanvända det CupNavi faktiskt hittat när respektive setupsteg nås.

Flöde:
1. Första setup-importen läser cupinfo, lag, grupper, planer/tider, regler, matcher/slutspel när de finns.
2. Resultatet granskas och sparas som ett cupbundet importunderlag.
3. Lag kan läggas in direkt.
4. Gruppkopplingar ligger kvar och dyker upp på Steg 3 som `Från första importen`.
5. Arrangören granskar och väljer aktivt att använda gruppindelningen. Befintliga grupper skrivs aldrig över.
6. Om ett helt importerat schema valts måste gruppstrukturen appliceras redan vid skapandet, eftersom matcherna annars saknar giltig gruppreferens. Underlaget ligger ändå kvar som referens på Steg 3.
