# CupNavi v397 – Admin core query reuse

## Mål
Göra de vanligaste adminsidorna Lag och Grupper snabbare mot fjärrdatabasen utan att ändra arbetsflödet.

## Förändringar
- **Lag:** laglistan laddas en gång och används både för antal registrerade lag och resten av sidan. Ett separat `COUNT(*)` + en andra `SELECT *` har tagits bort.
- **Lag:** tävlingsklasser från `sync_competition_classes()` återanvänds i både registrering och redigering i stället för nya identiska läsningar.
- **Grupper:** grupplistan laddas en gång och `len(groups)` används för befintligt antal grupper. Den senare identiska gruppläsningen är borttagen.
- Alla skrivningar som kan ändra lag/grupper följs redan av `st.rerun()`, vilket gör återanvändningen säker inom samma render.

## Varför
På Turso/annan fjärr-DB kostar varje extra roundtrip betydligt mer än att använda data som redan finns i minnet. Förändringen minskar standardvägen utan att lägga till cache som riskerar att visa gammal data.
