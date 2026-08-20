# CupNavi WEBTEST 2026.08.20-16

Den här versionen är avsedd för test på Streamlit Community Cloud.

## Filer som ska ligga i GitHub-repot

- `app.py`
- `requirements.txt`
- `.gitignore`

Lägg **inte** upp `turnering.db`, `.streamlit/secrets.toml`, Turso-token eller adminlösenord i GitHub.

## 1. Ersätt app.py

Filen `CupNavi_app_2026.08.20-16_WEBTEST.py` är den verifierade källfilen.
När den läggs i GitHub-repot ska den heta exakt:

`app.py`

## 2. requirements.txt

Använd den medföljande `requirements.txt`.

## 3. Streamlit Secrets

Öppna appen i Streamlit Community Cloud och gå till appens Settings/Secrets.
Lägg in de tre hemligheterna där med dina befintliga värden:

```toml
TURSO_DATABASE_URL = "..."
TURSO_AUTH_TOKEN = "..."
ADMIN_PASSWORD = "..."
```

Klistra inte in värdena i app.py eller GitHub.

## 4. Vad testaren ser

I molndrift öppnas appen i `Turneringsvy`. Endast publicerade turneringar visas där.
För att testa administration väljer testaren `Admin` i vänsterspalten och loggar in med adminlösenordet.

På sidan ska versionsmärket visa:

`KÖR VERSION 2026.08.20-16-WEBTEST`

I vänsterspalten ska det dessutom stå:

`Databas: Turso`

Om det står `Databas: Lokal SQLite` är Turso Secrets inte korrekt inlagda.

## 5. Viktig kontroll före extern testning

1. Öppna webbappen själv.
2. Kontrollera versionsnumret.
3. Kontrollera att `Databas: Turso` visas.
4. Kontrollera att Turneringsvy kan öppnas utan adminlösenord.
5. Byt till Admin och kontrollera att lösenord krävs.
6. Kontrollera att tidigare turneringsdata syns.
7. Lägg till ett testlag i en testturnering och kontrollera att det finns kvar efter omladdning.
8. Sätt maxantal lag till ett känt värde och kontrollera att nästa lag blockeras när gränsen är nådd.

## 6. Lokal körning

Lokalt, utan Turso-miljövariabler/Secrets, använder appen `turnering.db` precis som tidigare.

```powershell
cd "$HOME\Documents\fotbollsturnering"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```
