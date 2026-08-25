# QUALITY V164
Release: 2026.08.25-164-PUBLIC-CONTAINER-COMPAT

- Removed both remaining st.container(key=...) calls from the public share fragment.
- Share toggle/panel styling now uses HTML anchor classes instead of keyed Streamlit containers.
- Public render has a regression guard forbidding keyed containers.
- All v162/v163 desktop layout changes are retained.
- Release markers are hard-synced.
