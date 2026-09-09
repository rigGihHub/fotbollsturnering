# v301 — E2E public navigation contract

GitHub Actions showed the same timeout in Chromium, Firefox and WebKit while waiting for `section=tables` after a Playwright click. The public navigation is already rendered as real anchors with explicit `href` values. In Streamlit's rerendering DOM, the element can be replaced between Playwright's pointer dispatch and browser navigation, producing a test synchronization failure rather than evidence that the route itself is invalid.

The critical journey now validates each rendered anchor's real `href` and then navigates to that exact href before asserting URL and section content. This preserves verification of the production direct-link/navigation contract while removing dependence on a transient Streamlit DOM node surviving a synthetic click.

No production runtime logic was changed in this release.
