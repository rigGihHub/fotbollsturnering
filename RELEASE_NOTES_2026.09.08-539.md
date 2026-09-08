# CupNavi 2026.09.08-539 – Import hotfix

## Akut rättning

Streamlit kunde inte starta eftersom `app.py` importerade `release_ui_label` från `cupnavi_core.version`, men funktionen saknades i versionsmodulen. Det gav `ImportError` redan vid appstart.

## Ändrat

- Återställer `release_ui_label()` i `cupnavi_core/version.py`.
- Behåller den befintliga versionsvisningen i sidofältet.
- Synkar `APP_VERSION`, `APP_BUILD_VERSION` och `VERSION.txt` till v539.
- Ingen funktionell ändring av cup-, schema- eller matchlogik.

## Kontroll

- Direkt import av `APP_VERSION` och `release_ui_label` verifierad.
- `release_ui_label(APP_VERSION)` ger `Version v1.539`.
- `compileall` passerar.
