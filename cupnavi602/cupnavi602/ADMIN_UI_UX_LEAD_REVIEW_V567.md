# Ledande UI/UX-granskning — CupNavi v567

## Samlad bedömning
CupNavi har stark funktionell bredd men adminupplevelsen har vuxit genom många lager av förbättringar. Nästa designfas bör inte lägga till fler paneler; den bör minska samtidiga val och göra hela appen konsekvent beslutsdriven.

## Prioritet 1 — En tydlig primär handling per skärm
Varje huvudsteg ska svara på: Vad ska jag göra här? Vad är klart? Vad är nästa steg? Sekundära verktyg ska ligga bakom progressiv disclosure. Schema i v567 är mönstret: välj intention först, visa sedan rätt verktyg.

## Prioritet 2 — Gör 9-stegsflödet visuellt lugnare
Alla steg ska vara åtkomliga, men på mobil bör de fungera som en kompakt progressrad/stepper med aktuell position och möjlighet att expandera hela flödet. Nio fullvärdiga knappar tar för mycket first-screen-yta.

## Prioritet 3 — Separera Setup från Cupdag
Admin har två mentala lägen: förbered cupen och kör cupen live. Efter publicering bör standardhemmet skifta från setup-status till Cupdag: nästa matcher, rapportering, avvikelser, domare/planproblem och snabba åtgärder.

## Prioritet 4 — Statusspråk som är konsekvent överallt
Använd samma fyra tillstånd i hela admin: Ej påbörjat, Behöver åtgärd, Klart, Publicerat/live. Undvik flera parallella formuleringar för samma sak.

## Prioritet 5 — Designa för mobil först
Primär CTA inom tumräckvidd, maximalt en huvudkolumn, tabeller som kort när de blir smala, sticky lokal actions-rad där det verkligen hjälper, och inga kritiska kontroller gömda långt ned.

## Prioritet 6 — Minska visuellt brus
Färre container-i-container, färre samtidiga metrics, tydligare typografisk skala, mer whitespace och konsekvent användning av färg endast för status/handling. CupNavi ska kännas tryggt och snabbt, inte som en kontrollpanel med alla reglage framme samtidigt.

## Prioritet 7 — En global sök/kommandoingång
För vana arrangörer: sök efter lag, match, plan, kod eller adminsida från en och samma ingång. För nybörjare ska den vara sekundär och aldrig konkurrera med huvudflödet.

## Prioritet 8 — Förhandsgranskning som ett riktigt review-läge
Kontroll bör bli en visuell “så här kommer cupen se ut”-granskning: cupinfo, grupper, schema, publika sidor, koder/roller och varningar i en sammanhängande preview innan Publicera.

## Prioritet 9 — Bättre tomma lägen
Tomma sidor ska inte bara säga att data saknas. De ska visa ett exempel och en enda knapp: Lägg till första laget, skapa första gruppen, lägg till första planen osv.

## Prioritet 10 — Ett riktigt designsystem
Samla spacing, radius, typografi, statuschips, cards, buttons, forms, alerts och mobile breakpoints i ett gemensamt system. Det minskar drift mellan äldre och nyare delar av appen.

## Rekommenderad ordning
1. Mobile admin stepper + first-screen cleanup.
2. Setup/Cupdag mode separation.
3. Kontroll som preview/review-läge.
4. Global status vocabulary + design tokens.
5. Empty states and form consistency pass.
