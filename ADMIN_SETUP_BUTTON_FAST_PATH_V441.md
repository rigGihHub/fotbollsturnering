# CupNavi v441 — Admin/setup button fast path

## Goal
Make frequent navigation clicks in setup/admin feel immediate by eliminating explicit second reruns when the action only changes navigation/session state.

## Changes
- New-tournament wizard Previous/Continue now use callbacks that set the target step before Streamlit's normal rerun.
- Competition-rules navigation (back to setup, edit pitches/times, done) uses the same single-rerun pattern.
- Admin guide navigation now routes through a callback rather than button click + explicit `st.rerun()`.
- Loading the optional fairness analysis now sets its lazy-load state in a callback and lets the ordinary widget rerun do the work.
- No competition, scheduling, scoring, or publication rules changed.

## Performance principle
Pure state/navigation interactions should normally require one Streamlit render per click. Explicit reruns remain appropriate after data mutations where an immediate fresh DB read is required.
