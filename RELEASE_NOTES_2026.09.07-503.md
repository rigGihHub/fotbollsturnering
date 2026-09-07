# CupNavi 2026.09.07-503 – GUIDED ADMIN NAV FIX

## Fix
- `Fortsätt till Grupper →` på Lag-sidan navigerar nu korrekt till `Grupper`.
- Programmatisk adminnavigation synkroniserar nu både aktuell admin-sida och v502:s guidade flödeswidgets.
- Fixen gäller även andra CTA-knappar som använder samma `_set_admin_page`-navigering och förhindrar att en gammal selectbox-status skriver tillbaka föregående sida på nästa Streamlit-rerun.

## Omfattning
- Ingen ändring av cup-, match-, schema- eller databaslogik.
- Endast navigationssynk i adminflödet.
