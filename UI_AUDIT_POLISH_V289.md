# CupNavi v1.289 – UI audit & polish

## Scope
A full static UI pass was made across `app.py` and the extracted Streamlit view modules after the v1.288 style-system decomposition. The review focused on information density, responsive behavior, navigation consistency, stale UI text, touch targets, tabs/tables, and repeated high-density column patterns. No domain logic, persistence, scheduling, result concurrency, authentication, or database schema was changed.

## Findings

### Fixed in v1.289
1. **Stale visible version** – the sidebar still showed `Version v.1.266` even though the actual release chain had advanced. The visible label is now derived from the current build version and therefore follows every future release automatically.
2. **Wide mobile column rows** – several admin dashboards, control/status blocks, player forms, setup panels and diagnostics use 4–5 Streamlit columns. These are reasonable on desktop but are the most repeated source of cramped controls and metrics on phones. Rows with four or more columns now wrap to a two-column mobile grid, while ordinary one/two/three-column forms are left untouched.
3. **Metric label overflow** – metric labels may now wrap instead of forcing narrow cards wider than the viewport.

### Reviewed and retained
- The role switcher already has a dedicated mobile wrapping rule.
- Public tabs already support horizontal scrolling and compact mobile sizing.
- Public match cards, tables and bottom navigation already contain explicit mobile rules.
- Minimum 44–46 px touch targets and keyboard focus styles are already present.
- The admin information architecture already uses five top-level groups plus contextual secondary tools, which is materially better than exposing all admin pages at once.
- Accessibility controls for high contrast and larger text remain available.

## Remaining UI opportunities
These are candidates, not blockers for v1.289:
- Continue reducing duplicate headings/captions on a few secondary admin pages.
- Consider replacing some dense diagnostic metric grids with compact summary cards after real-device validation.
- Validate the new generic 4+/5-column mobile wrapping in physical Android/iPhone browsers before making more aggressive global responsive changes.
- `render_public_view` remains a large orchestration function and is still a good structural candidate, but no visual behavior was changed there in this release.

## Verification boundaries
The changes are presentation-only and covered by static/regression tests. Full browser E2E and physical Android/iPhone rendering are not claimed in this release.
