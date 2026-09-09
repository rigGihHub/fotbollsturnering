# CupNavi v1.305 – Admin lazy fairness speed

## Fokus
UI-förenkling och snabbare Adminöversikt utan ändringar i schema-, resultat-, auth- eller skrivlogik.

## Ändring
Fairnessanalysen hämtade tidigare alla schemalagda matchrader från databasen på varje render av Adminöversikten trots att sektionen var hopfälld. I Streamlit körs innehåll i en expander även när den är stängd, så detta var ett dolt read-only Turso/libSQL-anrop i standardflödet.

Från v1.305 körs fairnessanalysen först när arrangören väljer **Kör fairnessanalys**. Om Cup Control Center är aktiverat och behöver samma matchrader återanvänds en gemensam snapshot, så inget duplicerat matchanrop införs.

## Effekt
- snabbare standardrender av Adminöversikten
- mindre onödigt databasarbete
- tydligare UI: analysen är ett aktivt val i stället för dold bakgrundsberäkning
- befintlig felisolering för fairness finns kvar

## Oförändrat
Ingen ändring av databasschema, schemaalgoritm, resultat, publicering, auth eller concurrency/CAS.
