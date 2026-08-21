# CupNavi 2026.08.21-75-HOTFIX

- Alla kvarvarande gamla `one(...)`-anrop i app.py ersatta med `one_row(...)`.
- Fixar NameError i publik Resultat-vy när matchhändelser renderas.
- Hela app.py genomsökt efter samma typ av gammalt DB-helper-anrop.
- Regressionstest använder AST och kontrollerar att `one(...)` inte återkommer.
