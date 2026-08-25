# CupNavi staging v156

## Local
1. Copy `staging/.env.staging.example` to `.env.staging` and fill values.
2. For local HTTP, set `CUPNAVI_STAGING_HOST=http://localhost:8080`.
3. Run:
   `docker compose --env-file .env.staging -f docker-compose.staging.yml up --build`

## Real HTTPS staging
Point a DNS hostname at the staging server and set:
`CUPNAVI_STAGING_HOST=staging.your-domain.example`

Caddy will request/manage TLS automatically when ports 80/443 are reachable.

## Verification
- `/health`
- `python scripts/check_http_public_parity.py`
- `python scripts/check_pwa_installability.py`

The parity check is read-only.
