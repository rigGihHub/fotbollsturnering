# CupNavi v348 – Guided Cup Setup

Version: `2026.08.31-348-GUIDED-CUP-SETUP`

## Mål
En användare ska kunna skapa sin första cup utan att redan förstå cupadministration eller fotbollstermer.

## Förändringar
- `Tävlingsklasser` presenteras som **Vilka ska spela?** med förklaring av exempelvis P2014.
- `Kapacitet` presenteras som **Vad har ni tillgång till?**
- CupNavi använder den befintliga rekommendationsmotorn och sportprofilen för att visa ett komplett, begripligt startförslag.
- Förslaget visar grupper, gruppstorlekar, slutspel, uppskattat antal matcher, matchtid och rekommenderad vila.
- En förklaring **Varför rekommenderar CupNavi detta?** gör beslutet begripligt.
- Kapacitetsproblem visas innan användaren går vidare.
- `Använd CupNavis rekommenderade upplägg` kräver ett aktivt klick och sparar endast rekommenderade regel-/formatvärden.
- Knappen skapar inte grupper, matcher eller schema.
- Snabbstart har förenklats till `Redo att lägga till lag` och `Fortsätt → Lägg till lag`.
- Avancerade val heter nu `Finjustera regler och format (valfritt)`.

## Tekniskt
Ingen databasmigrering. Befintlig `recommend_tournament_format()` och sportprofil återanvänds. Ingen ändring av schemaalgoritm, matchskapande eller publicering.
