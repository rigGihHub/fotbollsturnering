# CupNavi v155 – Public parity gate

The public cutover now has an explicit release gate.

Checks:
1. Published match payload parity.
2. Group standings parity.
3. Published playoff/bracket parity.
4. Min cup summary parity.

CI creates a deterministic published tournament fixture and runs the parity gate.

For a real Turso cup:
- set `TURSO_DATABASE_URL`
- set `TURSO_AUTH_TOKEN`
- set `CUPNAVI_PARITY_CUP=<public_slug>`
- run `python scripts/check_public_parity.py`

The script does not write to the database.

Important: the current executable parity checker validates public data semantics
against independently materialized snapshots. A true cross-deployment HTTP parity
check should be added when the PWA API has a staging URL.
