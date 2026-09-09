# CupNavi v.1.234 – E2E Fresh DB State

E2E intentionally changes the SQLite database from pytest while Streamlit is running.
Production render caching cannot know about those out-of-process writes. In `CUPNAVI_E2E=1`
SELECT/PRAGMA queries now bypass the render cache and open a fresh database connection.
Production caching is unchanged. This addresses both stale public direct-link state and stale
active-tournament selector options while retaining all earlier submit/playoff hardening.
