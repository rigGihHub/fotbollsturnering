# CupNavi 2026.09.08-538 – Fragment Dataset Rerun Guard

Performance-only batch.

- Keeps the isolated public Matches fragment from v537 for local display interactions.
- Dataset-changing controls now deliberately re-enter the full public workspace:
  - match view (Alla/Kommande/Spelade)
  - match filter mode
  - Visa fler
  - tournament highlights
- This preserves server-side batching correctness: a 12-row first-paint snapshot is widened before controls that require data outside that batch.
- Weather/event-detail toggles remain fragment-local and fast because they only operate on the currently visible rows.
- Removes a redundant `sort_public_matches(...)` on every fragment rerun because the public-core SQL is already ordered and all supported filters preserve order.
- Avoids rescanning played matches for total goals when exact aggregate totals were already supplied by the cup-day database snapshot.

Focused tests: `tests/test_v538_fragment_dataset_rerun_guard.py`.
