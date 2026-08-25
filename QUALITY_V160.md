# QUALITY V160
Release: 2026.08.25-160-UX-FLOW-REFINEMENT
Schema: v21

Focus only: flow, logic and visual hierarchy.

- Canonical seven-step admin flow.
- Each core page explains purpose and current step.
- Publication, schedule and result status are visible in one place.
- Next recommended action is based on actual tournament state.
- Previous/next navigation follows the natural cup-building flow.
- Results page shows completion progress and public-visibility state.
- Mobile touch targets improved while deep functions remain in grouped navigation.

- Same-package hotfix: public match cards receive match-event data explicitly, preventing NameError after fragment/lazy-load refactoring.

- Same-package PWA hotfix: offline navigation with cup/team query parameters falls back to cached index.html; mobile E2E waits for service-worker control before offline reload.
