# CupNavi v398 – Admin overview snapshot reuse

Adminöversikten återanvänder nu den redan hämtade workflow-snapshoten ännu mer konsekvent.

- Control Center använder `unchecked_n` från snapshoten i stället för ett extra COUNT-anrop.
- Direktredigering återanvänder `teams_n` och `played_n` i stället för två extra COUNT-anrop.
- Full startkontroll hämtar inte längre hela grupper-, lag- och matchtabeller med tre `SELECT *`-frågor. Den använder snapshotens räknare för grupper, lag, matcher, tilldelning, schemaläggning, domare och publicering.
- Ingen ny cache införs; data gäller fortfarande den aktuella Streamlit-renderingen.

Målet är färre remote round-trips och mindre överförd data på Adminöversikten utan att ändra funktion eller beslutslogik.
