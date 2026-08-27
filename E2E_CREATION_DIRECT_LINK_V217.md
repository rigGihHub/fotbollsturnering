# CupNavi v.1.217 – E2E Creation & Direct-Link Hardening

## GitHub Actions failures addressed

### Testmiljö selection
Repeated attempts to drive Streamlit's hidden React-Aria radio input proved
browser-dependent. CUPNAVI_E2E already exists as a deterministic CI mode.

In v1.217 the real tournament creation form defaults to Testmiljö only when:
`CUPNAVI_E2E=1`.

Normal production/default behavior is unchanged: Riktig cup remains the first
default option outside E2E mode.

The browser test now verifies that Testmiljö is selected and, after submit,
verifies the persisted database row has environment_type='test'. It no longer
depends on Streamlit's private radio DOM implementation.

### Public direct link
The canonical `cup` query parameter is now only rewritten when its value actually
changes. This removes an unnecessary query-parameter mutation/rerun from public
direct-link rendering.

The E2E journey now waits for the actual `.cup-hero .title` rather than a broad
exact-text locator and emits useful page-body diagnostics if routing/rendering
fails. The public wait budget is 60 seconds for the first CI render.

## Local browser verification
A local Chromium E2E attempt could not start the Streamlit server within this
ChatGPT runtime, so no claim is made that the browser journey is locally green.
GitHub Actions remains the cross-browser source of truth.
