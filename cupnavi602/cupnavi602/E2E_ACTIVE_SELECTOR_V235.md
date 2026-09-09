# CupNavi v.1.235 – E2E Active Tournament Selector

## Root cause
After creating tournament A and then B, CupNavi intentionally keeps the existing valid
`active_tournament_selector` instead of overwriting it with the newly preferred cup.

Therefore A can already be the selected value when the regression test calls
`choose_streamlit_option(..., A)`.

Streamlit/React-Aria may omit the already-selected item from the popup option list.
The old helper still waited for an option named A and timed out even though the selector
was already correct.

## Fix
`choose_streamlit_option()` is now idempotent:
- if the requested value is already selected, it returns immediately;
- otherwise it opens the React-Aria popup and selects the requested option;
- after Streamlit rerenders, it verifies the new combobox value.

## Stronger regression journey
The active-tournament regression now performs an actual state change:
1. create A;
2. create B;
3. explicitly select B;
4. explicitly select A;
5. reload the browser;
6. assert A is still selected.

This is stronger than attempting to select A when A may already be active.
