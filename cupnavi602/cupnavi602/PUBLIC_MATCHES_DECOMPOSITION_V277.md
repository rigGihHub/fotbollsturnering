# CupNavi v1.277 – Public Matches Decomposition

## Mål

Fortsätta den kontrollerade nedbrytningen av `app.py` utan att ändra det publika användarflödet eller introducera nya beroenden.

## Genomfört

- Hela orkestreringen för publika **Matcher** har flyttats till `cupnavi_core/public_matches_view.py`.
- Streamlits `@st.fragment`-gräns ligger kvar i `app.py`, som nu endast anropar den extraherade vyn med explicita beroenden.
- Matchhändelsefrågan för synliga färdigspelade matcher har flyttats från UI-koden till `cupnavi_core/public_match_repository.py`.
- `app.py` behåller DB-anslutning och prestandamätning via `public_match_events_db_snapshot()`.
- Befintlig stegprofilering, inkrementell rendering, lag-/planfilter, vädertoggle och delningskontroll är bevarade.
- Ingen databas- eller schemamigration och inga nya dependencies.

## Arkitektur

Den publika matchvägen är nu tydligare separerad:

`app.py fragment/service boundary -> public_matches_view -> pure/view helpers + repository callback`

Repository-modulen är fortsatt fri från Streamlit/session state.

## Riskhantering

Ändringen är en beteendebevarande extraction. Kritisk persistence, matchrapportering, auth och concurrency-skydd har inte ändrats.

## Verifiering

Se release-rapporten för tester som faktiskt körts. Full browser-E2E och fysisk mobiltest ska inte betraktas som verifierade om de inte uttryckligen körts.
