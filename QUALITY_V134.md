# QUALITY V134

- Schema recovery now presents ranked, one-click corrective actions after scheduling failures.
- Recommendations distinguish real pitch-capacity shortage from softer team/preferences constraints.
- Direct actions include extending the last day's pitch windows, clearing late-start/late-match preferences, relaxing consecutive-match extra break, or adding a pitch.
- Pitches can be named while retaining pitch_number as the stable internal identifier.
- Pitch names are shown in key public, team-portal and admin schedule views.
- Database schema upgraded to v18 with idempotent compatibility repair for named pitches.
- Full pytest suite and Python compile checks required before release.
