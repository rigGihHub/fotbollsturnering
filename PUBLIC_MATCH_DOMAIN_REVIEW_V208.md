# CupNavi v.1.208 – Public Match Domain QA & Performance Review

## Review
After the v1.204–v1.207 decomposition, `render_public_view()` is 827 lines.
The match domain is now split into:
- public_match_cards.py
- public_match_filter_logic.py
- public_match_filters_view.py
- public_match_feed_logic.py

The review focused on remaining database work in the public match path rather than further mechanical extraction.

## Verified performance issue
Before v1.208, opening the public match page loaded every scoring/red-card event row for the entire tournament before the user had selected the final match subset. This query also ran when the user selected only upcoming matches, where no result events can be displayed.

## Implemented optimization
Event loading now happens after:
1. all/upcoming/played selection,
2. team/QR pitch filtering,
3. advanced public filters.

Only visible matches with complete results contribute match IDs to the event query.

### Query behavior
- Upcoming-only view: 0 event queries.
- Filtered view containing no played matches: 0 event queries.
- Played/all view: one event query scoped to the visible played match IDs.
- Previous behavior: one event query across the full tournament whenever the Match page rendered.

This is a query-count/data-volume optimization. No unmeasured wall-clock speedup is claimed.

## Preserved
- match-event display
- protected-player behavior
- red-card/goal display
- result logic
- filters
- URL state
- permissions
- persistence

## Next recommendation
Stop decomposing the public match domain for now unless browser/performance evidence identifies another concrete problem. The next architecture work should move to another high-risk large function or strengthen measured production telemetry.
