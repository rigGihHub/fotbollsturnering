# v1.270 – Incremental public match rendering

## Problem

Large published cups could render every filtered match card on the first public `Schema & resultat` load. On mobile this creates an unnecessarily large Streamlit delta/DOM even though only the first handful of matches are initially visible on screen.

## Change

- The public match list now renders at most 12 match cards initially.
- `Visa 12 fler matcher` adds one bounded batch at a time.
- Changing the actual filtered result set resets the view to the first batch.
- Player goal/red-card event rows are queried only for the match cards that are currently rendered, not all filtered played matches.
- Performance diagnostics record both `visible_matches` and `filtered_matches` so the effect can be compared after deployment.
- Paging policy lives in the framework-free `cupnavi_core/public_match_paging.py` module.

## Deliberate non-changes

No long-lived caching was added. Result/concurrency protections are unchanged. There is deliberately no `Visa alla` control because rendering hundreds of cards at once would defeat the mobile performance goal.
