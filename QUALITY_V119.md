# CupNavi QUALITY V119

Version: 2026.08.24-119-SHARE-VERSION-HOTFIX

## Scope
- Fixed persistent share control so the visible control renders a plain label instead of nested span markup.
- Public Turneringsvy no longer shows the technical CupNavi version in the sidebar.
- Admin/other authenticated modes retain version visibility for troubleshooting.
- Added focused regression tests for both behaviours.

## Verification
- Python syntax compilation: PASS
- Full pytest suite: 274 passed
- GitHub update package verified after packaging.
