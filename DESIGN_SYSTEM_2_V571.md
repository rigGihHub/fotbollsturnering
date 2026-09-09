# CupNavi v571 — Design System 2.0

## UX-bedömning
CupNavi har under många releaser fått lokala UI-förbättringar. Funktionerna är starka, men samma typ av komponent har ibland olika visuellt uttryck beroende på när sidan byggdes. Det skapar mer kognitivt brus än vad funktionaliteten kräver.

v571 lägger därför en **kanonisk presentationsnivå sist i CSS-kaskaden**. Historisk CSS raderas inte, eftersom äldre kontrakt och specialvyer fortfarande ska fungera, men den synliga produkten får ett sammanhållet språk.

## Principer
1. **En hierarki:** sida → sektion → kontroll → status.
2. **En primär handling:** grönt reserveras i huvudsak för nästa huvudåtgärd.
3. **Neutrala ytor bär struktur:** kort ska inte konkurrera med innehållet.
4. **Färg betyder något:** statusfärger får kommunicera information; dekoration hålls tillbaka.
5. **Samma kontrollspråk:** knappar, formulärfält, tabs, expanders, metrics och tomma lägen delar radier, typografi och rytm.
6. **Mobil först:** 46 px touchhöjd på små skärmar, horisontellt scrollbar tabs och 16 px inputtext lämnas åt befintligt mobillager.
7. **Tillgänglighet:** tydlig focus-visible och reduced-motion respekteras.

## Konkreta förändringar
- Ny tokenfamilj `--cn2-*` för färg, spacing, radie och kontrollhöjd.
- Standardiserad rubrik- och sektionshierarki inklusive `.cn-section-head`.
- Primär/sekundär knapp får samma proportioner över hela appen.
- Fält, select, datum/tid och formulär får samma fokus- och kantlogik.
- Kort, metrics, expanders och custom CupNavi-kort normaliseras till neutrala ytor utan onödiga skuggor.
- Alerts behåller Streamlits semantiska färg men får samma form och typografi.
- Tabs och segmented controls görs tydligare som navigation/val, inte som extra kort.
- Empty states standardiseras.
- Dataframes/Text-TV-tabeller får samma täta men läsbara bordsyta.
- Mobil touchhöjd höjs till 46 px i det sista designlagret.

## Varför ett separat slutlager?
`style_system.py` innehåller historiska designlager från många releaser. En stor radering nu skulle ge hög regressionsrisk. v571 är därför avsiktligt ett **final override layer** som laddas efter både det äldre produktsystemet och mobilstilarna. Det ger en kontrollerad migreringsväg. Senare kan äldre regler tas bort stegvis när skärm-för-skärm-regression är verifierad.

## Efter deploy bör visuellt kontrolleras
- Android: Adminöversikt, Planer & tider, Schema, Kontroll.
- iPhone-smal bredd: Åtkomst & koder-tabs och formulär.
- Desktop: Mina cuper, Adminöversikt, Cupdagen.
- Publik vy: matchkort, tabeller och statistik så att v571 inte gör dem för administrativa.
