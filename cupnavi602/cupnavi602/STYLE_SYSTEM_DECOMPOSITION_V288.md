# CupNavi v288 – Style system decomposition

Version: `2026.08.29-288-STYLE-SYSTEM-DECOMPOSITION`

## Bakgrund

Efter v287 gjordes en ny storleks-/risk-audit av `app.py`. De största kvarvarande top-level-blocken var den globala CSS-/designsysteminjektionen, databasinitering, schemamotorn och den publika huvudvyn. CSS-/designsystemfunktionerna gav klart störst möjlig radminskning med lägst domän- och persistensrisk.

## Ändring

Sex presentationsfunktioner har flyttats från `app.py` till `cupnavi_core/style_system.py`:

- `inject_custom_css`
- `inject_ux2_css`
- `inject_v191_design_system`
- `inject_v193_product_design_system`
- `inject_v266_public_mobile_css`
- `inject_v198_visual_system`

Den nya modulen tar Streamlit- och component-objekten som explicita beroenden. Modulen importerar därför inte app-, databas- eller persistenslager.

`app.py` behåller tunna kompatibilitetswrappers med samma funktionsnamn och samma anropsmönster som tidigare. Befintlig ordning för CSS-injektion, Streamlit-rendering och keyboard-komponenter är därmed oförändrad.

## Riskavgränsning

Ingen databaslogik, auth, schemamotor, resultatpersistens, concurrency/CAS, publiceringslogik eller domänlogik har flyttats eller ändrats.

Detta är en strukturell dekomposition av presentationskod, inte en visuell redesign.

## Regressionstester

Äldre tester som kontrollerade CSS direkt i `app.py` har uppdaterats för den nya modulgränsen. Beteendekontrakten för tokens, responsive breakpoints, accessibility, toolbar, mobile navigation och keyboard shortcut ligger kvar.

Nytt fokuserat kontrakt: `tests/test_v288_style_system_decomposition.py`.
