# CupNavi v405 – Cupday direct actions

## Goal
Make Cupdagen more operational without adding dashboard noise or database work.

## Changes
- Per-pitch cards now show approximate lateness when a not-started match has passed kickoff.
- A kickoff delayed at least five minutes gets a direct action to compare delay-recovery options. The existing Cupverktyg delay workspace is prefilled with pitch and delay.
- Opening a late, live, or result-due match from Cupdagen now carries the exact match into Resultat.
- Resultat keeps that focused match first in the editable list and explains that it was opened from Cupdagen.
- Existing data snapshots and delay tooling are reused; no Cupdagen query was added.
