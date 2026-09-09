# CupNavi v1.267 – Performance baseline

## Syfte
Efter flera optimeringsvarv går CupNavi över från antagandebaserad optimering till mätning per faktisk vy/rerun.

## Ändringar
- En kompakt performance-snapshot registreras för varje Streamlit-rerun: route, total render-tid, DB-tid, DB-anrop, writes och render-cacheträffar.
- Första renderingen i browser-sessionen skiljs från efterföljande warm reruns.
- Adminöversiktens befintliga Prestandadiagnostik visar nu även de senaste rutterna, så t.ex. Turneringsvy/Matcher kan jämföras med Admin/Schema.
- `CUPNAVI_PERF_LOG=1` kan aktiveras i drift för enradiga JSON-loggar utan extern analystjänst.
- Dubbla `@st.fragment` på Cupinfo-renderingen togs bort. Det var en onödig dubbel wrapper runt samma fragment.
- Ingen långlivad data-cache och inga concurrency-skydd har tagits bort.

## Nästa mätsteg
Kör publik Android-resa och jämför first_render mot warm_rerun. Om DB-andelen är låg men total render hög ligger nästa sannolika flaskhals i Streamlit/render/frontend snarare än databasen.
