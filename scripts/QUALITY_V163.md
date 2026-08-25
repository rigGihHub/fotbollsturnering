# QUALITY V163
Release: 2026.08.25-163-PUBLIC-RUNTIME-FIX

Root cause: v162 used st.container(key=...) in the public follow-team area.
That API is not compatible with the Streamlit runtime currently serving CupNavi,
so rendering stopped immediately after the tournament status banner.

Fix:
- removed key= from st.container
- retained compact desktop styling without requiring keyed containers
- kept all v162 desktop-density changes
- hard-synced all release version markers
