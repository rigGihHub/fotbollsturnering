# Publicera fotbollsturneringen

Appen använder vanlig SQLite lokalt. När `TURSO_DATABASE_URL` och
`TURSO_AUTH_TOKEN` finns använder den i stället en permanent Turso-databas.

## 1. Skapa molndatabasen och behåll befintliga data

Installera Turso CLI i WSL enligt Turso-dokumentationen och logga in. Kör sedan
från mappen där `turnering.db` ligger:

```bash
turso auth login
turso db create fotbollsturnering --from-file ./turnering.db
turso db show fotbollsturnering --url
turso db tokens create fotbollsturnering
```

Spara databasadressen och token separat. En tom databas kan i stället skapas med
`turso db create fotbollsturnering`.

## 2. Lägg projektet på GitHub

Följande filer ska finnas i samma projektmapp:

- `app.py`
- `requirements.txt`
- `.gitignore`

Lägg inte upp `turnering.db` eller `.streamlit/secrets.toml` på GitHub.

## 3. Publicera på Streamlit Community Cloud

1. Öppna https://share.streamlit.io och anslut ditt GitHub-konto.
2. Välj projektets repository och `app.py` som startfil.
3. Öppna **Advanced settings** och välj Python 3.14.
4. Klistra in följande i **Secrets**, med de riktiga värdena:

```toml
TURSO_DATABASE_URL = "adressen från turso db show fotbollsturnering --url"
TURSO_AUTH_TOKEN = "..."
```

5. Klicka på **Deploy**.

Efter publicering ska samma turneringar visas efter omstart och från olika
telefoner/datorer. Ändringar i appens kod publiceras automatiskt när de pushas
till GitHub.

## Lokal körning

Utan molnhemligheterna fortsätter appen använda `turnering.db`:

```powershell
cd "$HOME\Documents\fotbollsturnering"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```
