# UX revision — first implementation stage, 2.8.0

Baseline: GitHub main 6cc732a, September 23, 2026. This is a staged migration,
not a claim that all requested workflows have been visually accepted.

## Audit and priority

1. P0: supplied public test URL cannot be reviewed. Browser renders a fetch error;
   direct public API reports HTTP 404, `Cup not found or not published`. No cup
   was republished, recreated or modified to bypass this. Admin requires sign-in.
2. P1: roster-specific fixed columns leak into unrelated generic admin lists.
   Scope those rules to the roster; keep access, activity and other cards single-column.
3. P1: public schedule starts with old completed matches, has no team filter and
   can omit playoff-only matches. Deduplicate match IDs, prioritize live/upcoming,
   and add a shared team filter plus an explicit team view.
4. P1: many independent public stylesheet generations fight over table columns.
   Replace the standings and match-card class families, with a single owner in
   design-system.css. Eight columns remain in the DOM and CSS at narrow widths.
5. P1: playoff visibility excludes placement-only snapshots; playoff cards ignore
   kit settings. Correct both without changing tournament data or ranking rules.
6. P1: statistics loading effect cancels itself when its loading flag changes.
   Use stable request dependencies and show retryable errors for statistics/tables.
7. P1: admin guide, sticky sidebar and large controls compete for mobile space.
   Four workflow phases, native mobile step selector, short guide with optional
   completion details; destructive cup controls are behind a disclosure.
8. P1: reporter sync banner overlays controls and green online can coexist with
   unsaved changes. Keep status in normal flow, show pending as warning, add match
   search and finished-match filter. Preserve server permissions and queue rules.

## Design foundation

Navy identity, teal primary action, white cards on pale neutral canvas. Dedicated
success/warning/error colors. 4/8/12/16/24/32 spacing, 12px cards, minimum 44px
controls, visible keyboard focus, reduced-motion support. Compact persistent brand
header includes release number. cn-* components are isolated from legacy rules.
Legacy bridges are explicitly marked; full deletion of old CSS requires further
signed-in regression testing across import, planning and permission screens.

## Checks

- Production Next build and TypeScript.
- Matchday ordering, deduplication, team resolution, placement format visibility,
  home-only/no-kit display, eight-column table semantics and workflow navigation.
- CSS cascade at 320, 360, 390, 430, 700, 760, 1024 and 1440 pixels. This is a
  selector/layout-rule check, NOT a browser screenshot or proof of text fit.
- Existing reporter login, placement playoffs, import navigation, team asset and
  weather regression scripts.

## Still required before declaring the total revision complete

Authenticated owner/local admin/reporter/team-leader walkthroughs, actual browser
screenshots at 360/390/430 and desktop, real published tournament tables and all
playoff formats, full import/review/schedule/publication workflows and remaining
legacy stylesheet consolidation. No backend authorization or production match
results are changed by this release.
