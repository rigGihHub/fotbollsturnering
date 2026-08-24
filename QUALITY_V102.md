# CupNavi QUALITY V102

Version: 2026.08.24-102-LIFECYCLE-HISTORY

## Scope
- Language-neutral tournament lifecycle: `draft`, `published`, `live`, `completed`, `trashed`.
- Completed cups stay publicly browsable as historical archives and become read-only in Admin until reopened.
- Permanent public slugs are generated once and remain stable even if cup metadata changes. Numeric `?cup=<id>` links remain backward compatible.
- Public selector distinguishes live and completed cups and sorts active cups before history.
- Admin can mark a cup live, complete it when all published scheduled matches are reported, reopen it, move it to Trash, restore it, or permanently delete it after typing the exact cup name.
- Schema migration v8 adds lifecycle/history fields.

## Verification
- Python syntax compilation: PASS.
- Full pytest suite: PASS — 215 tests.
- Regression tests added in `tests/test_lifecycle_v102.py`.
