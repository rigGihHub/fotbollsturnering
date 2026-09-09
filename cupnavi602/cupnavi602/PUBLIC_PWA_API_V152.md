# CupNavi v152 – standalone public PWA/API foundation

This release adds a parallel public product path without replacing Streamlit production.

## Run locally
API:
`uvicorn cupnavi_api.main:app --reload --port 8001`

PWA:
`python -m http.server 8080 -d public_pwa`

Open `http://localhost:8080/?cup=<public-slug-or-id>`.

If API and PWA are served on different origins, set `window.CUPNAVI_API_BASE`
before `app.js` or reverse-proxy `/api/` to the API service.

## Important limitations
- The API repository currently supports SQLite via `CUPNAVI_API_SQLITE_PATH`.
- Production Turso/PostgreSQL wiring is deliberately not guessed.
- The PWA is not production-live until hosted on HTTPS with the service worker at its public scope.
- v153 adds server-side standings, playoff payloads and followed-team summaries using shared competition logic.


## v153 endpoints
- `/api/public/cups/{key}/standings`
- `/api/public/cups/{key}/playoffs`
- `/api/public/cups/{key}/teams/{team_id}/summary`
