# CupNavi v.1.218 – E2E Expander State Fix

## Failure
The active-tournament-switch journey creates two tournaments in the same browser session.

The E2E helper previously clicked the `Skapa ny turnering` expander title
unconditionally on every create attempt. On the second call the expander could
already be open, so the click closed/toggled the native `<details>` element.
During Streamlit's rerender/animation the `<details>` layer intercepted pointer
events for the `Skapa` submit button.

## Fix
The helper now:
1. locates the sidebar `<details>` containing `Skapa ny turnering`;
2. reads its native `open` state;
3. clicks its `<summary>` only when it is closed;
4. waits until the expander is actually open;
5. resolves the form inside that expander;
6. waits for the real `Skapa` button to be visible/enabled before submitting.

The test therefore no longer changes expander state accidentally between first
and second tournament creation.

No CupNavi business logic changes in v1.218.
