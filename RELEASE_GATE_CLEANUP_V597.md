# CupNavi v597 – Release Gate Cleanup & Full Relevant Regression

## Why
The current release gate still selected a small number of historical assertions whose exact copy, navigation target, or version pin had been intentionally superseded by v591–v596. Those failures made the gate noisy and unable to distinguish a real regression from test archaeology.

## Classification of the six v596 gate failures
- v566 required/optional pitch copy: superseded by the v593 two-step Planer & tider flow; current required state and optional address/travel controls remain.
- v566 referee-next copy: superseded by v594; referees remain explicitly optional and the forward CTA remains.
- v567 schedule back target: intentionally superseded by the nine-step flow; Schema now correctly goes back to Domare.
- v575 exact rules labels: superseded by v591 novice-first rules copy; progressive disclosure remains.
- v575 exact played-match safety sentence: wording changed, safety contract remains: played matches are never moved automatically and schedule changes mark the schedule dirty.
- v589 exact release version: historical version pin only; v589 team-flow behavior remains covered semantically.

## Gate policy now
Historical release-specific files remain untouched for archaeology. The current gate no longer selects superseded exact-copy/version assertions. It selects evergreen tests, safety/functional contracts, surviving semantic v589 team-flow tests, v596 import-symbol smoke tests, and a new v597 current-state semantic contract.

A selected current-gate failure is a blocker. We do not delete old tests just to create green output.
