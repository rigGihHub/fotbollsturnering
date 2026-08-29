# CupNavi v1.295 – Public workspace decomposition

## Mål
Fortsätta den stegvisa dekompositionen av `app.py` utan att ändra publik funktionalitet, databasmodell eller skrivgränser.

## Ändringar
- Hela den återstående orkestreringen i `render_public_view` har flyttats till `cupnavi_core/public_workspace_view.py`.
- `app.py` behåller en tunn adapter och injicerar befintliga tjänster/funktioner via `PublicWorkspaceDependencies`.
- Publik hero, Följ mitt lag, navigation, matchfragment, Tabeller, Slutspel, Statistik, Cupinfo, informationsskärm och besöksanalys behåller samma ordning och befintliga underliggande moduler.
- DB- och integrationsfunktioner ägs fortfarande av applikationslagret och injiceras. Den nya workspace-modulen öppnar ingen egen DB-connection och utför inga direkta INSERT/UPDATE/DELETE.
- Äldre source-location-regressionstester har flyttats till den nya faktiska ägaren av beteendet i stället för att försvagas.

## Riskbedömning
Strukturell förändring med medelhög yta men låg avsiktlig beteendeförändring. Ingen schema-, auth-, resultat-, publicerings- eller concurrency/CAS-logik ändras.

## Verifiering
- Fokuserade regressionskontroller för workspace-gränsen.
- Samtliga top-level `tests/test_*.py` körs i batcher inför release.
- `compileall`, release-manifest och ZIP-integritet verifieras.
- Full Playwright/Streamlit-E2E kan inte köras i denna miljö om Streamlit saknas och ska då inte rapporteras som passerad.
