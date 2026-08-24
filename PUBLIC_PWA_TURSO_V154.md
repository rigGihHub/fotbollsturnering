# CupNavi v154 – PWA/Turso parity

## API database selection
The standalone public API now uses the same cloud environment variable names as
the Streamlit application:

- `TURSO_DATABASE_URL`
- `TURSO_AUTH_TOKEN`

If both are present, the API reads from Turso through `libsql`.
If they are absent, it falls back to `CUPNAVI_API_SQLITE_PATH` or `turnering.db`.

The API is read-only. It does not run migrations or write tournament data.

## CORS
`CUPNAVI_PWA_ORIGINS` can contain a comma-separated allowlist of PWA origins.
Use the real HTTPS PWA origin in production instead of `*`.

## Security
The public API no longer returns the full tournament database row. Tournament
metadata is explicitly allowlisted before it leaves the repository.

## PWA
v154 adds CupNavi branding, live/next match center, improved match cards,
directions links, practical tournament information and online/offline status.

The PWA is still parallel to Streamlit until it has real HTTPS hosting and has
been tested against the production Turso database.
