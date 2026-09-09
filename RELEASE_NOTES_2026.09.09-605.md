# CupNavi v605 — Theme Architecture Rebuild

## Varför
v602–v604 visade att flera historiska CSS-lager konkurrerade med varandra. Resultatet blev olika tema på publik- och admindelar, vita legacy-ytor och mörk text på mörk bakgrund.

## Ändrat
- Lagt ett sista, auktoritativt CupNavi-designsystem som styr appskal, sidebar, typografi, surfaces, inputs, alerts och knappar.
- Gemensam mörk marin/svart grund för publik och admin.
- Cyan används för aktiv navigation/fokus; grönt reserveras för positiva/commit-statusar.
- Förbättrad kontrast för headings, brödtext, captions, labels och disabled-kontroller.
- Legacy-expander/form/bordered containers neutraliseras till samma mörka surface-system.
- Publik hero och admin delar samma visuella språk.
- Text-TV-tabeller behåller svartare sportdatayta och blir visuellt separerade från övrigt UI.
- Kalendern behålls avsiktligt ljus för läsbarhet.
- Desktopens 3x3 setup-matris ersätts av en kompakt 9-stegsrad. Mobilflödet behålls separat.

## Release gate
- Python compileall: PASS
- v605 current release gate: 5/5 PASS
