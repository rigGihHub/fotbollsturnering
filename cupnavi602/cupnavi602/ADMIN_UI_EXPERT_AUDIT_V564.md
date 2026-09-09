# CupNavi v564 – UI-expertgranskning av admin

## Bedömning
Admin hade rätt funktioner men för mycket konkurrerande navigation innan sidans egentliga innehåll. Det tydligaste problemet var att nio huvudsteg, Övrigt, en stor kodknapp, förklarande text och sök låg staplade före arbetsytan. På mobil gav det onödigt lång väg till den uppgift användaren faktiskt försökte göra.

## Principer för v564
1. **Huvudflödet är fortfarande alltid synligt.** Kravet från tidigare versioner behålls: Cupinfo → Lag → Grupper → Regler → Planer & tider → Domare → Schema → Kontroll → Publicera.
2. **Sekundära funktioner får lägre visuell prioritet.** Övrigt och Åtkomst & koder visas som en kompakt rad och ser inte ut som steg 10 och 11.
3. **Kortare orientering.** “Du är här” ersätts visuellt av en kompakt stegrad, exempelvis “Steg 4 av 9 · Regler”.
4. **Mina cuper ska alltid vara nära.** När en cup är öppen finns “← Mina cuper” i vänsterflanken tillsammans med aktiv cup och miljö.
5. **Åtkomstcenter delas efter uppgift.** Administratörer, koder och profil ligger i egna flikar så användaren inte behöver skrolla genom allt.
6. **Sök är ett verktyg, inte ett flödessteg.** Sök ligger kvar hopfällt och stör inte normal cupadministration.

## Kvar att visuellt verifiera efter deploy
- Android: att 3×3-flödet inte klipper långa etiketter.
- Smala iPhone-bredder: flikarna Administratörer/Koder/Min profil.
- Desktop: att vänsterflankens Miljö → Cup → Mina cuper upplevs tydlig utan dubbel navigation.
- Kontrollera verklig first paint och scrollposition med en cup som har många lag och matcher.
