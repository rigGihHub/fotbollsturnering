# CupNavi 2026.09.09-607 — Broadcast Control Visual Rebuild

A visual rebuild based on the deployed v606 screenshots. The goal is not another color patch; Streamlit is treated as the runtime while CupNavi owns the visual shell.

## Changed
- One uninterrupted dark canvas across header, main workspace and sidebar.
- Explicit styling for `stMain`, `stMainBlockContainer`, native forms, expanders, metrics, tables and inputs to stop white Streamlit islands from resurfacing.
- Sidebar reduced to a quiet navigation rail rather than a competing dashboard.
- Stronger typography hierarchy and substantially higher text contrast.
- Compact 9-step cup journey retained and visually normalized.
- Cup/marketing hero upgraded into a restrained broadcast panel.
- Aqua reserved for direction/focus; green/amber/red remain semantic status colors.
- Text-TV surfaces remain deliberately near-black and visually distinct from the admin shell.
- Calendar remains intentionally light for legibility.

## Release integrity
`app.py`, `VERSION.txt` and `cupnavi_core/version.py` use the same v607 identifier.

## Scope
Visual shell only. No tournament, scheduling, scoring, permissions or persisted-data behavior is intentionally changed.
