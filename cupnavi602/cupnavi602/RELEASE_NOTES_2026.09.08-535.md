# CupNavi v535 – Public First-Paint Narrow Rows

Performance-only release.

- Narrows the public first-paint match row for limited server-side match snapshots.
- Stops serializing/transferring `tournament_id`, `bracket_id`, `round_no` and `referee_id` when the landing view does not consume them.
- Keeps user-visible fields needed by cards, filters, penalties, winners, referee name and pitch name.
- Keeps the complete legacy/full-data query unchanged for advanced filters and fallback routes.
- Applies to both future-cup first batches and cup-day first-batch/live-window snapshots.
