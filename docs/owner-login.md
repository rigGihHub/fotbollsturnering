# CupNavi owner login

CupNavi supports one environment-only owner credential for emergency/creator access.

Required server environment variables:

- `CUPNAVI_OWNER_EMAIL`
- `CUPNAVI_OWNER_PASSWORD`

The credential is never stored in GitHub or the database. A successful owner login receives a normal signed CupNavi admin session with `role=owner`. The owner role can list and access all cups, while ordinary organizer accounts continue to use `organizer_accounts` and `tournament_members`.

Security rules:

- owner login uses the same rate limit as ordinary login
- secrets are compared with constant-time comparison
- owner sessions have the same 12-hour expiry and HMAC signature as organizer sessions
- no owner secret is returned by the API
- no hard-coded fallback password is permitted
