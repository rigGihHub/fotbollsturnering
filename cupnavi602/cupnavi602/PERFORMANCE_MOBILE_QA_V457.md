# CupNavi v457 — Performance + Mobile QA

## Syfte
Post-freeze utvecklingsrelease som kan förberedas utan deploy. v456 är fortsatt go-live-kandidaten tills den klarat skarpt genrep.

## Prestanda
- Skärpt budget för `Turneringsvy/Mitt lag`:
  - första render: 1800 ms / 5 DB-anrop
  - varm interaktion: 850 ms / 2 DB-anrop
- Skärpt budget för `Admin/Adminöversikt`:
  - första render: 2300 ms / 9 DB-anrop
  - varm interaktion: 1050 ms / 3 DB-anrop
- Befintliga fast-path-kontrakt ligger kvar: publik kärnsnapshot, lazy matchdata, in-memory mobilslutspel och callback-baserade interaktioner.
- Ingen ny DB-fråga eller explicit rerun har lagts till i v457.

## Mobil QA
Granskat primärt 360–430 px:
- knappar/länkar: minst 44 px
- select/text/number-input: minst 44 px
- checkbox/radio: minst 44 px tryckyta
- expanders: minst 44 px
- publika lag-/matchtexter bryts vid extrema långa namn
- Mitt lag-kortet får inte driva horisontell overflow
- <=390 px kolumner staplas fortsatt till full bredd
- tabeller och flikar behåller kontrollerad horisontell scroll där den faktiskt behövs

## Viktigt
Detta är statisk/regressionstestbar mobil-QA. Exakt Samsung/iPhone-rendering måste fortfarande verifieras efter deploy på riktiga enheter.
