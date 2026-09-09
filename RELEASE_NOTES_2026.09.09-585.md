# CupNavi 2026.09.09-585-REVISION-FIX-SUGGESTIONS

## Revision conflict repair suggestions

- When selected revision changes create blocking schedule conflicts, CupNavi now searches for small, concrete alternatives before the organizer applies anything.
- Suggestions are conservative and preview-only. CupNavi first tries another known pitch at the same kick-off, then small time shifts (5-minute steps, up to ±60 minutes) on known pitches.
- A suggestion is shown only if the complete selected revision becomes blocker-free under the same consequence checks used before write.
- Suggestions can still carry non-blocking warnings such as short rest; those remain visible.
- Pressing “Använd detta förslag i granskningen” only updates the review preview. Nothing is persisted until the organizer presses “Tillämpa valda matchändringar”.
- Applied suggestion overrides are cleared after successful persistence.
- If no safe one-match adjustment is found, CupNavi points the organizer to Schema for larger replanning.

## Safety retained

- Started/played matches remain protected.
- Confirmed pitch windows, pitch/team/referee overlaps, phase-specific match duration and minimum rest remain part of the consequence check.
- Revision documents never silently rewrite the schedule.
