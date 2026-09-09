# CupNavi v157 – Mobile PWA E2E

## Automated mobile coverage
The dedicated GitHub workflow installs Chromium and tests the PWA using:
- Pixel 7 emulation
- iPhone 14 emulation
- all four bottom-navigation destinations
- followed-team / Min cup
- offline app-shell reload after an online visit

## Real HTTPS staging validation
When staging exists:
- set `CUPNAVI_STAGING_BASE_URL=https://...`
- optionally set `CUPNAVI_PARITY_CUP=<public slug>`
- run `python scripts/check_https_staging.py`

The check validates HTTPS, API health, manifest, service worker, key security
headers and optionally a real public cup endpoint.

## Limitation
Chromium device emulation is not the same as physical Safari on an iPhone.
Before a public cutover, install/offline behavior should still be checked on
at least one real Android device and one real iPhone.
