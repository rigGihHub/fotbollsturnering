# CupNavi v596 – IMPORT HOTFIX

## Problem
Streamlit startup failed at `app.py` when importing `release_ui_label` from `cupnavi_core.version`.

## Root cause
`app.py` still imported `release_ui_label`, but `cupnavi_core/version.py` had been reduced to only `APP_VERSION` in releases after v591. This made the application fail before rendering any UI.

## Fix
- Restored `release_ui_label(version)` in `cupnavi_core/version.py`.
- Synchronized `APP_BUILD_VERSION`, `cupnavi_core.version.APP_VERSION`, and `VERSION.txt` to v596.
- Added `tests/test_current_release_gate_v596.py` so the imported symbol and version synchronization are explicitly tested.
- Added the v596 hotfix test to the current release gate.

## Verification
- `python -m py_compile app.py cupnavi_core/version.py`: PASS.
- Direct import `from cupnavi_core.version import APP_VERSION, release_ui_label`: PASS.
- v596 regression tests: 3/3 PASS.
- Evergreen suite: 302 passed, 2 deselected.
- The broader selected historical gate still contains superseded UX/version assertions from older releases; these are unrelated to the import hotfix and are not reported as a clean full-gate pass.

No deployment is performed by this package.
