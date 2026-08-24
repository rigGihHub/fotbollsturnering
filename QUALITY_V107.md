# CupNavi QUALITY V107

Version: 2026.08.24-107-UPDATE-HOTFIX

## Scope
- Hotfix for GitHub update packaging: `cupnavi_core/qol.py` was omitted from the v106 minimal update package even though `app.py` imports it.
- GitHub update packages must now include the complete `cupnavi_core/` directory to prevent mixed/missing core modules.
- No product/database behavior changes beyond version metadata.

## Verification
- Python syntax compilation: PASS.
- Full pytest suite: PASS — 235 tests.
- Regression test verifies every direct `cupnavi_core.<module>` import from `app.py` exists as a packaged module.
