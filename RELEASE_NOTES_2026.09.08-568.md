# CupNavi v568 — Mobile Admin Stepper

## Why
The nine-step setup map is valuable on desktop but consumed too much of the first screen on phones. Admin work should start with the current task, not three rows of navigation.

## Changed
- Desktop keeps all nine setup steps visible.
- Mobile shows the current `Steg X av 9` context plus Previous, Next and `Alla 9 steg`.
- `Alla 9 steg` opens the complete jump list; no setup destination is removed.
- The current step remains visually explicit and disabled in the jump list.
- Secondary tools remain outside the numbered setup flow.

## Safety
This is a navigation/presentation change only. Tournament data, schedule generation, publication validation and permissions are unchanged.
