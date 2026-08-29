# CupNavi v1.272 – Public data decomposition

- Builds on v1.271.
- Moves the read-only public visitor/leader SQL out of `app.py` into `cupnavi_core/public_match_repository.py`.
- Keeps Streamlit session handling and performance timing in `app.py`.
- Preserves one-query behavior and fresh live data; no cache, schema, dependency or persistence change.
- Purpose: reduce coupling in the 18k-line entrypoint in a small regression-testable step rather than rewrite the application.
