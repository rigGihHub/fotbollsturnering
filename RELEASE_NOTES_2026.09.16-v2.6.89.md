# CupNavi v2.6.89

- Tog bort elva orefererade Next-komponenter, inklusive fem ersatta cupskapare och gamla återanslutnings-/guideomslag.
- Tog bort död CSS för den ersatta delningsknappen; delning ägs nu av den globala sidhuvudfunktionen.
- Rättade release-gaten så att migration 36 kontrolleras utan att felaktigt kräva att den fortfarande är senaste schema.
- Produktionscontainern för FastAPI använder nu en separat beroendelista utan Streamlit och pandas.
- Uppdaterade Streamlit→Next-granskningen med aktuell paritet och en uttrycklig plan för behåll, migrera och radera.
