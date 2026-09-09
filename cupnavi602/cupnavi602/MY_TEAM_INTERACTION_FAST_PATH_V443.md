# CupNavi v443 – My Team Interaction Fast Path

Release: `2026.09.04-443-MY-TEAM-INTERACTION-FAST-PATH`

## Fokus

Minska väntetid i den publika **Mitt lag**-vyn och kapa onödigt arbete på Matcher före första resultatet.

## Förbättringar

- Lagvalet i **Mitt lag** använder nu `on_change` och behöver inte längre en extra explicit fragment-rerun.
- **Visa mitt lags matcher** och **Visa alla lag** använder callbacks och går via en enda normal Streamlit-rerun.
- Matchers översiktsfråga för skytteligaledare hoppas över helt tills det faktiskt finns minst ett spelat resultat. Innan dess kan ingen skytteligaledare finnas, så den tidigare DB-frågan gav inget användarvärde.
- Performance Contract bevakar nu även Mitt lag-interaktionerna.

## Säkerhet / beteende

Ingen tävlingslogik, poängmodell, schema- eller resultatlogik är ändrad. URL-parametrarna för lagval och matchfilter bevaras.
