# v335 – Live Match Next Match Flow

CupNavi Score now offers a one-tap transition to the next later playable match that does not yet have a complete saved result.

- The shortcut is shown only after the current match has a persisted result.
- It uses the existing chronological scheduled-match ordering.
- Already reported matches are skipped.
- The shortcut never jumps backwards in the schedule.
- Selection is changed through a Streamlit widget callback; there are no database writes in navigation.
- Existing result saving, optimistic locking, live events, undo, bulk input and playoff handling are unchanged.
