# CupNavi v531 – Defer first-paint analytics

- Removes the visitor analytics database write from the first public render.
- The first render only marks the visitor session locally in Streamlit session state.
- The analytics UPSERT runs on the next public rerun/interation and remains throttled to once per five minutes.
- Trade-off: visitors who leave before any interaction can be undercounted, in exchange for lower first-paint latency.
- No tournament, schedule, match or result data semantics changed.
