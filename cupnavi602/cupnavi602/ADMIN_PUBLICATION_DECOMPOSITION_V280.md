# CupNavi v1.280 – Admin publication decomposition

## Scope

The publication/start controls and public lifecycle presentation have been moved out of `app.py` while guarded write operations remain in the application layer.

## Changes

- Added `cupnavi_core/admin_publication.py` for pure warning classification, publication blockers, action labels and completion readiness.
- Added `cupnavi_core/admin_publication_view.py` for sidebar/mobile publication controls and lifecycle buttons.
- Added `cupnavi_core/admin_publication_repository.py` for the read-only published-match lifecycle count query.
- `app.py` keeps `_set_publication_if_current` and `_set_lifecycle_if_current`, preserving compare-and-set/concurrency protection.
- No schema, migration or authentication changes.

## Compatibility intent

Existing behavior is preserved: colour/kit warnings remain advisory, schedule errors and unapproved blocking warnings prevent publication, first publish vs update uses `published_once`, mobile and sidebar publication share the same validation state, and completion still requires all published scheduled matches to have results.
