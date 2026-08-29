# CupNavi v1.273 – Public navigation decomposition

## Syfte
Fortsätta den kontrollerade nedbrytningen av `app.py` utan att förändra publik funktionalitet eller införa nya beroenden.

## Ändrat
- Publik navigations-HTML har flyttats från `render_public_view()` till den rena modulen `cupnavi_core/public_navigation_view.py`.
- Routingdefinitionerna ligger fortsatt i `public_view_logic.py`; den nya modulen ansvarar endast för HTML, URL-kodning och escaping.
- Den befintliga enda responsiva sticky-navigationen och `team`-parametern bevaras.
- `app.py` ansvarar nu endast för aktuell sida/state och Streamlit-rendering i denna del.

## Risk
Låg. Ingen databas-, schema-, auth- eller sessionmodell ändras. Ingen dependency tillkommer.

## Verifiering
Riktade v1.273-regressionstester kontrollerar aktiv sida, fem länkar, teamparameter, URL-kodning, HTML-escaping samt att inline-navigationen inte återinförs i `app.py`.
