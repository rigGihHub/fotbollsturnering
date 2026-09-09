# CupNavi v294 — Public style cleanup

## Why
The public tournament orchestrator still contained a large inline CSS block for the followed-team experience, live strip and desktop layout. The block also contained nested/unbalanced media-query structure, which is invalid CSS and can make responsive behavior browser-dependent.

## Changes
- Moved the public follow/live/layout CSS from `render_public_view` to `cupnavi_core/style_system.py`.
- Added `inject_public_experience_styles(st)` as the single presentation boundary for these rules.
- Rewrote the media-query structure as independent valid `max-width:900px`, `min-width:901px` and `max-width:760px` blocks while preserving the existing declarations.
- Kept all tournament routing, data access, result logic, publication logic and persistence unchanged.

## Risk
Low-to-medium presentation-only change. The intended visual declarations are unchanged, but previously invalid nested media-query structure is now valid and deterministic across browsers.
