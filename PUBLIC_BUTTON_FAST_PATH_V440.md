# CupNavi v440 — Public Button Fast Path

Version: `2026.09.04-440-PUBLIC-BUTTON-FAST-PATH`

## Varför
Publika CupNavi används ofta från mobil under pågående cup. Några av de mest frekventa publika knapparna gjorde fortfarande först Streamlits normala widget-rerun och därefter ett explicit fragment-rerun. Det gav två renderingspass för ett enda tryck.

## Förändrat
- Global sökning: **Rensa** använder nu callback och behöver bara den normala rerunnen.
- Global sökning: träffar för **lag, match och plan** navigerar via callback utan ett extra fragment-rerun.
- Matcher: **Visa hela cupen** efter lagfilter använder callback.
- Matcher: **Visa fler matcher** uppdaterar renderingsgränsen i callback och undviker dubbel render.
- Query-parametrar och session state sätts före renderingen, så nästa vy kan byggas direkt i samma normala rerun.
- Performance Contract bevakar nu de publika single-rerun-vägarna.

## Effekt
Fyra högfrekventa publika interaktioner går från två Streamlit-renderingar till en. Ingen ny databasfråga, cache eller domänlogik har lagts till.

## Avgränsning
Detta är ett fokuserat prestandasteg. Nästa pass bör fortsätta med admin/setup-knappar och kvarvarande explicita reruns, samt fortsatt cold-start-profileringsarbete.
