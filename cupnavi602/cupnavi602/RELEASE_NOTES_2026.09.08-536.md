# CupNavi v536 – Adaptive Public Rerun Cache

Performance-only release.

- Keeps the active cup-day public fragment cache epoch at 3 seconds.
- Extends the epoch to 12 seconds for future cups, where results are not changing live.
- Extends the epoch to 30 seconds for finished cups, where published public data is effectively static.
- Reduces avoidable render-cache clearing on public filter, paging and toggle interactions.
- Falls back to the existing 3-second behavior when cup dates are missing or invalid.
