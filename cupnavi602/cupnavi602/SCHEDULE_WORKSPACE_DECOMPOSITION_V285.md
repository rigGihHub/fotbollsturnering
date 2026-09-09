# CupNavi v1.285 – Schedule workspace decomposition

Version: `2026.08.29-285-SCHEDULE-WORKSPACE-DECOMPOSITION`

## Scope

The admin page **Skapa och publicera schema** has been extracted from `app.py` into
`cupnavi_core/schedule_workspace_view.py`.

The extracted workspace owns the Streamlit orchestration for:

- schedule quality and rule summary,
- whole-schedule generation/update,
- recovery guidance,
- per-group status,
- lazy PDF export and travel information,
- visual schedule board,
- drag-and-drop ordering,
- manual time/pitch/referee adjustment,
- schedule table and bulk score editing.

## Persistence boundary

The schedule engine and write-sensitive operations remain owned by `app.py` and are
injected into the workspace. New narrow callbacks preserve the existing SQL semantics for:

- undoing schedule edits,
- persisting drag-and-drop slot updates,
- saving one manually adjusted match,
- bulk-saving changed score rows.

No database schema, migration, authentication, publication rule or concurrency model was changed.

## Size

`app.py` decreased from 16,629 lines in v1.284 to 16,064 lines in v1.285.

## QA

The release adds `tests/test_v285_schedule_workspace_decomposition.py` and updates older
source-location tests so they validate the new module boundary rather than requiring the UI
implementation to remain in `app.py`.
