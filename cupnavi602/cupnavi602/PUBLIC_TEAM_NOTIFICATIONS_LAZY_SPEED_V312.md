# CupNavi v1.312 – Public team notifications lazy speed

## Ändring
Den publika vyn **Följ mitt lag** hämtade tidigare de fem senaste lagnotiserna från databasen på varje rerun så snart ett lag var valt, även när notislistan låg i en stängd expander och användaren inte läste den.

I v1.312 är notishistoriken explicit lazy via **🔔 Visa senaste lagnotiser**. Databasfrågan körs först när besökaren aktiverar visningen. Om inga notiser finns visas ett tydligt tomläge.

## Oförändrat
- Val av favoritlag och delbar laglänk.
- Nästa match, tabellposition och möjlig slutspelsmatch.
- Vägbeskrivning till nästa plan.
- Formuläret för att prenumerera på e-postnotiser och all skriv-/verifieringslogik.
- Schema, resultat, publicering, auth, DB-schema och concurrency/CAS.

## Effekt
Standardrenderingen för en vald lagvy slipper en onödig `notifications`-query. Det minskar databasarbete på en publik mobilnära vy utan att ta bort funktionalitet.
