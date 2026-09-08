# CupNavi v544 – Mobile Reporter Grace Window

## Matchrapportör – mobil först
- Större touchytor för rapportörens knappar (minst 64 px).
- I Avancerad rapportering visas **Snabbrapportera mål** direkt vid aktuell match.
- När målskyttsstatistik är aktiv väljs målskytt i rullista från respektive lags matchtrupp/laglista.
- Varje lag har stora **+ / −**-knappar bredvid sin målskyttsrullista.
- **+** sparar matchresultat och målskytt atomiskt i samma transaktion.
- **−** korrigerar vald spelares senaste mål och matchresultatet atomiskt.
- Ingen spelare behöver letas fram genom en lång skrollista under matchen.

## 15 sekunders korrigeringsfönster
- Alla centrala rapportörsåtgärder markerar senaste redigeringstid.
- Under de första 15 sekunderna visas ett tydligt korrigeringsfönster med instruktion att kontrollera och använda minus/Ångra vid fel.
- Själva databasskrivningen sker fortfarande direkt. Detta är avsiktligt: en fördröjd DB-skrivning skulle kunna tappas om mobilen tappar nät eller sidan stängs. Korrigeringsfönstret ger snabb rättning utan att offra datasäkerheten.

## Mobilaviseringar – 30 sekunders debounce
- Goal-push-payload innehåller `deliver_after` +30 sekunder och ett `debounce_key` per match/sida.
- Ett nyare mål för samma lag/match markerar äldre väntande målnotis som `superseded`.
- En snabb mål-korrigering med minus avbryter väntande målnotis för laget/matchen.
- Pushleveransworker är fortfarande framtida funktionalitet, men outboxen är nu förberedd för regeln “30 sekunder från senaste redigering”.

## Verifiering
- `tests/test_v544_mobile_reporter_grace_window.py`: 3/3 gröna.
- `python -m compileall -q app.py cupnavi_core`: grön.
- Äldre reporter-tester har kvar historiska versionsassertioner mot v525 och faller därför endast på versionssträng, inte på den testade reporterlogiken.
