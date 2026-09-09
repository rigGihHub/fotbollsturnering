# CupNavi v537 – Isolated Matches Fragment

Performance-only release.

- Public Matches gets its own Streamlit fragment boundary.
- Match-page widget interactions (paging, filters, weather, event details and highlights) can rerun the Matches workspace without rerunning the full public workspace shell.
- Parent public workspace still owns routing and core data selection on a normal/full public navigation run.
- No change to match semantics, live freshness, publication or schedule behavior.
