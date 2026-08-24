# CupNavi QUALITY V118

Version: 2026.08.24-118-RELEASE-SYNC

## Scope
- QA/release synchronization hotfix only.
- Ensures GitHub package contains complete cupnavi_core including ux2.py.
- Removes stale hard-coded version expectations from the active release package by shipping the complete current tests folder.
- Adds RELEASE_MANIFEST.txt and release-sync regression tests.

## Verification
- Python syntax compilation: PASS.
- Full pytest suite: PASS.
- GitHub update package is verified after packaging.
