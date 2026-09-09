# CupNavi v315 – Public native navigation speed

## Problem

The public Cupinfo / Schema & resultat / Tabeller / Slutspel / Statistik menu used ordinary HTML `href` links. Even after v314 moved the shell earlier in the render order, every section click still performed a browser/query-string navigation rather than a normal in-session Streamlit widget interaction.

## Change

The five primary public sections now use a native `st.segmented_control` inside a keyed sticky container.

- Section changes remain inside the active Streamlit session.
- `section=` is synchronized back to `st.query_params` so canonical deep links remain available.
- A selected team query is preserved when present.
- The five-column green sticky navigation shell is retained through targeted CSS.
- Tournament data, scheduling, results, playoffs, authentication and persistence logic are unchanged.

## Expected effect

The menu interaction should feel materially more immediate because a click no longer relies on a full HTML-link navigation before Streamlit renders the selected section. The selected page can still have its own data-loading cost after the navigation state changes.
