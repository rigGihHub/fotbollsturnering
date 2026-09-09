# CupNavi v.1.219 – Initial Setup Hardening, Phase 3

## Goal
Reduce database reads during ordinary Streamlit reruns without introducing stale caching or changing autosave behavior.

## Optimizations
- Reuse the already loaded played-match count for class locking.
- Load competition classes once per setup render instead of three times.
- Batch team counts with one `GROUP BY competition_class_id` query instead of one `COUNT(*)` query per class plus a separate total-team query.
- Reuse the current widget-derived `_planned_total` for format recommendation.
- Reuse the already ensured pitch-day windows for both capacity metrics and format recommendation instead of querying the same windows again.

## Query impact
For a tournament with N competition classes, the targeted changes remove approximately `N + 5` data-read/helper calls from a normal setup rerun:
- 1 duplicate played-match count;
- 2 duplicate competition-class reads;
- 2 duplicate pitch-window reads;
- N reads from replacing per-class counts + total count with one grouped count query.

Example: with two competition classes, that is about 7 fewer targeted reads per rerun.

This is a query-count reduction, not a claimed wall-clock speedup. Production timing was not measured here.

## Safety
No global cache was added. The setup still reads fresh data on each Streamlit rerun.
No forms were introduced and autosave semantics remain unchanged.
