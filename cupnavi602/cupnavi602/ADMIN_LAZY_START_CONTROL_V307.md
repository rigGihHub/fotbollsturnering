# CupNavi v307 — Admin lazy start control

## Mål
Förenkla och snabba upp Adminöversikten utan att ändra cupens domänlogik.

## Ändring
Sektionen **Publicering & startkontroll** gjorde tidigare tre fulla read-only hämtningar (grupper, lag och matcher) på varje render trots att sektionen var hopfälld. Streamlit-expanders är inte lazy.

Kontrollen är nu opt-in via **Visa full startkontroll**. Först när den aktiveras hämtas grupper, lag och matcher och de befintliga readiness-kontrollerna visas.

## Oförändrat
- publiceringslogik
- schemavalidering
- schemaalgoritm
- resultat
- databasstruktur
- auth
- concurrency/CAS
