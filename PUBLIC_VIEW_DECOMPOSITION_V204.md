# CupNavi v.1.204 – Public Matches Decomposition Phase 1

## Scope
The public match-card renderer is extracted from the nested `render_public_view`
implementation into `cupnavi_core/public_match_cards.py`.

## Preserved in app.py
- match filtering
- URL/query state
- result/event loading
- live/upcoming/recent orchestration
- tournament/session state
- database access

## Extracted
- match card HTML/presentation
- played/upcoming/live status presentation
- kit color presentation
- weather presentation inside cards
- referee presentation
- empty match-card state

The nested `_render_public_match_cards` function remains as a thin adapter so
existing call sites and fragment behavior remain unchanged.
