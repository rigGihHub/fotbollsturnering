# CupNavi v334 – Live Match Score + Events Combined

Version: `2026.08.31-334-LIVE-MATCH-SCORE-EVENTS-COMBINED`

## Förändring

Matchrapportörens CupNavi Score visar nu snabbregistrering av matchhändelser direkt under samma valda match när ett resultat finns sparat. Rapportören kan därför ändra/spara resultat och därefter registrera mål, assist, gula och röda kort utan att byta arbetsyta eller välja matchen igen.

Den befintliga mobilinmatningen för händelser är utbruten till en gemensam renderer som används både av CupNavi Score och den separata Matchhändelser-vyn. Ångra senaste, spelarbyte, lagval, matchtruppsfilter, mål/assist-validering och optimistic locking använder därför samma kodväg i båda vyerna.

Matchhändelser aktiveras i kombinationsvyn endast när matchen har ett senast sparat resultat. Ett osparat resultatutkast används aldrig som valideringsgrund för händelser. Den separata Matchhändelser-vyn och tabellen för massinmatning finns kvar.
