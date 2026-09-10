# CupNavi v613 — Frontend migration foundation

## Beslut
CupNavi ska inte längre försöka skapa hela sin visuella identitet genom Streamlit-CSS. Streamlit behålls under en kontrollerad övergång, men den nya publikupplevelsen byggs fristående i Next.js/React.

## Det som är implementerat i v613
- `frontend-next/` — ny Next.js App Router-frontend.
- Server-side hämtning mot befintligt read-only FastAPI `/api/public/...`.
- CupCover som egen CupNavi-komponent.
- Matchday Cards med tröjsiluetter och Text-TV-resultatfönster.
- Text-TV 330-tabell som isolerat live/data-lager.
- Slutspels- och cupinfo-yta med samma design-DNA.
- Responsiv mobil layout.
- Ingen förändring av befintlig Streamlit-runtime eller databaslogik.

## Nästa migrationssteg
1. Verifiera publikvyn mot verklig publicerad cup.
2. Flytta publikens lagfokus/favoritlag, PWA och notiser.
3. Skapa autentiserat admin-API med tydlig command/query-gräns.
4. Migrera adminens startsida och cupflöde stegvis.
5. Ta bort Streamlit först när motsvarande flöden är verifierade i nya frontenden.
