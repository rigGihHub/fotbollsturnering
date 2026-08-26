# CupNavi v.1.203 – Public Statistics Decomposition

Phase 3 extracts the public tables/toplists/playoff renderer from app.py into
cupnavi_core/public_statistics_view.py.

The app keeps a thin @st.fragment adapter. Database/domain helpers remain owned
by app.py and are injected into the extracted renderer. Business rules,
persistence, permissions and tournament data are unchanged.

This reduces the main-file change surface and makes public statistics/playoff
presentation independently testable without touching the match renderer.
