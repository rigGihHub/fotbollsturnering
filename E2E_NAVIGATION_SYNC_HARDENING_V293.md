# v1.293 – E2E navigation sync hardening

## Root cause
The v1.292 CI log showed three identical public-navigation failures. The browser clicked a real public navigation link but the test called `wait_app()` immediately; that helper could succeed against the previous Streamlit DOM before the URL navigation committed. The assertion therefore inspected stale Schema content while expecting Tabeller. The supplied Android screenshot already showed that Tabeller itself rendered, so this was treated as an E2E synchronization defect rather than a table-domain regression.

The active-tournament switch failure was a second E2E robustness issue: the helper assumed one combobox click always produced a visible `[role=listbox]`. Streamlit reruns can replace the widget between lookup and click, and popup markup differs between Streamlit/browser engines.

## Changes
- Public section journey now waits for the expected `section=` URL before asserting page content.
- It then waits for the expected domain token to become visible.
- Active-tournament helper reacquires the selectbox across reruns and retries opening it.
- Popup lookup supports semantic option roles plus current React-Aria/BaseWeb popup containers.
- Production navigation, tables, database and business logic are unchanged.

## Verification
Focused static/regression tests and compile checks are included in the release. Full Playwright execution requires the browser/Streamlit E2E environment and must not be claimed unless actually run.
