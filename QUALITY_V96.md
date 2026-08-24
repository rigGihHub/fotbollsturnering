# CupNavi QUALITY V96

Version: 2026.08.24-96-CUPDAY-EXPERIENCE

## Scope
A broad cup-day experience release above v95.

Implemented first production/MVP versions of:
- Min cup / follow a team with bookmarkable team URL and in-app notifications.
- In-app notifications for schedule moves, delays and reported results.
- Schedule impact / what-if analysis for pitch, referee and team-rest conflicts.
- Multisport profiles (football, floorball, handball, ice hockey, basketball, volleyball, tennis, padel, other) with sport defaults.
- CupNavi Score quick result entry.
- Digital team check-in.
- Referee centre inside the restricted reporter workspace with assignment acknowledgement.
- Automatic pitch-delay shifting with preview and team notifications.
- Playoff forecast based on current group tables.
- Tournament map/practical venue points.
- QR codes per pitch that open a pitch-filtered public view.
- CupNavi readiness/quality score (0-100).
- Change history and undo for supported new schedule/sport actions.
- Public tournament feed.
- Offline browser draft for match scores (localStorage safety net; not full PWA sync).
- Automatic tournament summary.

## Important limitations
- Browser/OS push notifications are not implemented; notifications are currently shown inside Min cup.
- True offline-to-server automatic synchronization is not possible in the current Streamlit-only architecture; v96 stores a local browser draft that can be recovered when connectivity returns.
- Sport profiles provide defaults/terminology, while some deep sport-specific scoring models (for example tennis game-by-game scoring) remain future work.
- Audit history starts with v96 actions and does not reconstruct older changes.

## Verification
- Python syntax compilation: PASS.
- Full pytest suite: PASS — 190 tests before final package verification.
- Schema migration v5 added and migration tests pass.
- New regression coverage in `tests/test_experience_v96.py`.
