# CupNavi v1.248 – E2E regression fix

GitHub Actions reported four browser failures after the simplification/mobile releases.

## Root causes
1. The lifecycle test still expected the `Skapa testdata:` button to be directly visible.
   The production UX now intentionally keeps Testverktyg inside a collapsed expander.
   The application behavior was correct; the browser test had not been updated to the
   new interaction path.
2. The active-tournament selector relied on React-Aria exposing every popup entry with
   role `option`. The supplied run showed that this assumption was not stable in the
   current CI/browser combination.

## Fix
- Lifecycle E2E now opens the real **Testverktyg** expander before locating/clicking
  `Skapa testdata:`. The test still exercises the actual Streamlit UI; it does not seed
  demo data behind the UI.
- `choose_streamlit_option()` keeps the semantic `option` lookup as first choice and
  falls back to exact visible text inside the active `listbox` when the browser/Streamlit
  markup does not expose the expected option role.
- The existing no-op handling for an already-selected value remains.

No production tournament logic, mobile layout, scheduling, persistence or selector
application behavior was weakened to satisfy the tests.
