# CupNavi v1.262 – Public summary UX

## Changes

- Added an approximate **Visitors now** counter to the public summary.
  - Recomputed on every public page render.
  - Counts the current Streamlit session plus other visitor sessions active within the recent activity window.
  - Uses the existing privacy-friendly anonymous session tracking; no IP address is stored.
- Moved **Cupinfo** to the leftmost position in the public navigation.
  - The same source of truth controls desktop and mobile navigation.
- Moved **Share tournament** from the hero/header area to directly below the public summary metrics.
  - Keeps the header cleaner and uses the previously empty space beneath the metrics.
  - Existing WhatsApp, email, SMS, QR and QR download features are preserved.

## Safety / performance

- No long-lived public cache was added.
- Active visitor counting is a single narrow COUNT query on the existing visitor_sessions table.
- Existing visit tracking, privacy model and publication behavior remain unchanged.
