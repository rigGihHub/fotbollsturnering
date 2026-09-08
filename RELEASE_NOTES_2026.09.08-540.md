# CupNavi v540 – Imported schedule repair + public summary fix

## Fixed: imported/photo schedules with critical errors can now be rebuilt
- A photo/PDF-imported schedule is stored with `schedule_locked=1` to prevent accidental overwrite.
- Previously the ordinary **Skapa om schemat** path still respected those locks, so critical imported schedule errors could survive regeneration unchanged.
- When an existing unplayed schedule has critical validation errors and locked matches, the primary action is now **Reparera och bygg om schemat**.
- The organizer must still explicitly confirm that existing times may be replaced.
- The scheduler then treats locked unplayed matches as replaceable for that explicit rebuild.
- The repository unlocks/resets only unplayed matches inside the same database transaction before applying the newly generated schedule.
- Matches with registered results remain protected.

## Fixed: literal `</div>` box in public Matches view
- The compact public summary HTML is now emitted as one continuous HTML block.
- This avoids a Streamlit Markdown/fragment edge case where an indented closing tag could surface as a visible code-like `</div>` box after fragment reruns.

## Safety
- Lag, grupper and tournament rules are not rewritten by schedule repair.
- Existing played results are not unlocked/reset by the repair transaction.
