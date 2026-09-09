# CupNavi 2026.09.08-566 – Planer & tider: novice UX

## Varför
UI-granskningen av adminflödet visade en tydlig friktion: steg 5, Planer & tider, pekade fortfarande på Adminöversikten. En oerfaren arrangör behövde därför förstå var planverktygen gömde sig i stället för att få en egen arbetsyta.

## Ändrat
- Planer & tider är nu en egen adminroute och en riktig sida i 9-stegsflödet.
- Sidan börjar med endast obligatoriska val: antal planer, namn och tillgängliga tider.
- Samma avsparkstider på alla planer ligger tydligt i kärnflödet och behåller CupNavis rekommenderade standard.
- Adresser och restider ligger under ett hopfällt frivilligt avsnitt och blockerar inte nästa steg om de inte används i planeringen.
- Ändringar i plankapacitet, synkronisering eller plantider markerar befintligt schema som i behov av ny kontroll, men skriver aldrig över spelade matcher.
- Tydlig sparstatus, klar-status och direkt navigation Regler ← Planer & tider → Domare.
- Adminöversiktens blockerare och rekommendationer länkar nu till den riktiga Planer & tider-sidan.

## UX-princip
En förstagångsanvändare ska kunna förstå steg 5 utan att känna till CupNavis övriga verktyg: "Hur många planer har vi? När kan de användas?" Allt annat är sekundärt.
