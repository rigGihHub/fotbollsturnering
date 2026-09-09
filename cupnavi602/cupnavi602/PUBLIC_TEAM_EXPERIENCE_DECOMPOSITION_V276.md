# v1.276 – Public Team Experience Decomposition

## Syfte
Fortsätta den stegvisa nedbrytningen av `app.py` utan att ändra produktbeteende,
persistence eller datamodell.

## Genomfört
- Hela den interaktiva publika **Mitt lag**-panelen flyttad till
  `cupnavi_core/public_team_follow_view.py`.
- Lagval, query-param-uppdatering, lagöversikt, vägbeskrivning, snabbfilter till
  lagets matcher, e-postprenumerationsformulär och senaste lagnotiser ägs nu av
  view-modulen.
- Ren teamlogik utökad i `cupnavi_core/public_team_follow.py` med testbara
  hjälpfunktioner för grupp-ID, tabellposition och möjlig slutspelsmatch.
- DB-/persistencefunktioner ligger kvar i `app.py` och injiceras i view-modulen.
  Ingen ny databasarkitektur eller dependency införs.

## Riskhantering
- Befintliga Streamlit keys och query-param-namn är bevarade.
- Befintlig notislagring och e-postfunktion återanvänds oförändrad.
- Ingen migration eller schemaändring.
- Kritisk matchrapportering/concurrency berörs inte.

## Resultat
`app.py` minskar med drygt 100 rader och den publika teamupplevelsen får en
separat testbar modulgräns utan rewrite.

## Reliability-fix upptäckt under audit
`public_match_filters_view.py` tog redan emot `source_team_id` som dependency men
refererade i fyra filtergrenar till det gamla app-lokala namnet
`_public_source_team_id`. Det kunde ge `NameError` när användaren valde
klass-, grupp-, lag- eller planfilter. Alla fyra grenarna använder nu den
injicerade resolvern och ett regressionstest låser kontraktet.
