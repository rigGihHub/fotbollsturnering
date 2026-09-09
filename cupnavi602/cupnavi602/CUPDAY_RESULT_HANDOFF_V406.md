# v406 – Cupday result handoff

## Why
A match opened from Cupdagen already stayed focused in Resultat (v405), but after the score was saved the operator fell back into the generic results workspace. On a busy pitch this creates unnecessary navigation and makes the next operational action unclear.

## Change
- When the focused Cupdagen match receives a complete score, CupNavi remembers that exact completion for one rerun.
- Resultat then shows the next pending scheduled match on the same pitch, using the match snapshot already loaded by the workspace.
- A primary action returns directly to Cupdagen, where that pitch is already visible in the operational view.
- If the pitch has no remaining pending matches, the handoff says so instead of inventing a next step.
- The generic search focus is cleared only for the completed Cupdagen handoff, so normal search behavior is unchanged.

## Performance
No new database query is introduced. The next match is selected in memory from the existing results snapshot.
