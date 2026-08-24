# QUALITY V157
Release: 2026.08.24-157-MOBILE-PWA-E2E
Schema: v21

- Playwright mobile E2E for Pixel 7 and iPhone 14 emulation.
- Tests mobile bottom navigation, followed-team view and offline app-shell.
- Dedicated GitHub browser-test workflow installs Chromium.
- Runtime PWA API-base config added before app.js.
- HTTPS staging checker validates TLS URL, health, manifest, service worker and security headers.
- Physical iPhone/Android testing is still explicitly required before public cutover.

Local sandbox note: Chromium navigation to localhost is blocked by the execution environment (`ERR_BLOCKED_BY_ADMINISTRATOR`), so the browser E2E is configured for GitHub CI and was not claimed as locally executed.
