# CupNavi QUALITY V101

Version: 2026.08.24-101-DOMAIN-FOUNDATION

## Scope
- `https://cup-navi.com` är nu CupNavis officiella publika basadress.
- QR-koder, delningslänkar, laglänkar och planlänkar går via den centrala publika basadressen.
- Streamlit-adressen finns kvar endast som dokumenterad legacy-/hostingadress i konfigurationen.
- `CUPNAVI_PUBLIC_URL` kan fortfarande användas som miljövariabel för framtida hosting/miljöer.
- Versionsvarningen i Admin visar tydligare vilka två versionskällor som inte matchar och hur den ska åtgärdas.
- Ingen databas- eller turneringslogik ändrad.

## Verification
- Python syntax compilation: PASS.
- Full pytest suite: PASS.
- Regression tests added in `tests/test_domain_v101.py`.
