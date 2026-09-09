# v437 – Publication validation fast path

- Full schema validation no longer runs after ordinary interactions on every admin page.
- Validation is recomputed where it is actually needed: Schema and Kontroll.
- Other admin pages may reuse only a known-fresh validation snapshot.
- A dirty or missing validation snapshot can never enable publication; the sidebar instead directs the organiser to Kontroll.
- Draft cups skip the published-match lifecycle count query entirely.
- Goal: reduce perceived thinking time without weakening publication safety.
