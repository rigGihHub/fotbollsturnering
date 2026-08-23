# CupNavi QUALITY V92

Version: 2026.08.23-92-PUBLIC-UX

## Omfattning
- Ny publik huvudnavigation med tre stora mobilvänliga val: Matcher, Tabell & statistik och Info.
- Spelschema och resultat sammanslagna i Matcher; spelade matcher visar resultat/händelser och kommande visar VS/tid/plan.
- Befintliga filter för alla matcher, grupp, lag och plan bevarade. Väder är fortsatt opt-in.
- Tabell & statistik samlar grupptabeller, skytteliga, assistliga, kortstatistik och slutspel.
- Info bygger regler dynamiskt från cupens faktiska turnerings- och schemainställningar.
- Arrangörens egen information, arena, kiosk, kontakt, Instagram, funktionärer, partners, erbjudanden och feedback finns på Info.
- Sponsorlogotyp, nivå och länk bevaras i publik Info-vy.
- v90:s lazy-load/cacheprinciper bevaras: matchhändelser laddas endast på Matcher; statistik och Info hämtas endast när respektive huvudsida väljs; väder/QR är fortsatt opt-in.

## QA
- Syntaxkontroll: `python -m py_compile app.py cupnavi_core/*.py`
- Full testsuite: `pytest -q` — 175 tester passerade
- Regressionstest: `tests/test_public_ux_v92.py`
