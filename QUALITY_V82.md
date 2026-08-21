# CupNavi 2026.08.21-82-HOTFIX

Fix:
- `import re` återinförd i app.py.
- Korrigerar produktionsfelet `NameError: name 're' is not defined` på bland annat sponsorsidan.
- Samma import krävs av språkfunktionens fallback-översättning och annan befintlig regex-logik.
- Regressionstest säkerställer att `re` är importerat när modulen används.
