# CupNavi v1.296 – Public presentation decomposition

## Scope
A low-risk structural extraction from `app.py` focused on public/group presentation helpers. No tournament scheduling, persistence, authentication, publication state or concurrency behavior was changed.

## Changes
- Added `cupnavi_core/public_presentation_view.py`.
- Moved the full presentation implementations for:
  - `render_group_table`
  - `render_bracket_tree`
  - `public_match_events_html`
  - `public_rules_html`
- `app.py` retains thin compatibility wrappers and injects existing database/domain helpers into the extracted module.
- Existing callers therefore keep the same function names and signatures.
- Reduced `app.py` from 13,766 to 13,387 lines (379 lines).

## Risk controls
- Database queries used by bracket/event presentation are still supplied by the application layer.
- Existing source resolution, translations, sport profiles and playoff qualifier logic are reused rather than duplicated.
- No DB schema, writes, CAS/concurrency, schedule engine, auth or lifecycle changes.

## Verification
- Focused v296 module-boundary and behavior tests added.
- Full top-level pytest suite run in batches.
- `compileall`, release manifest check and ZIP integrity verified before packaging.
- Browser E2E and physical-device verification are not claimed unless separately executed.
