# CupNavi v399 – Mobile playoff clarity

The public playoff view now preserves the outcome details that desktop already communicated when viewed on a phone.

- Winning teams are highlighted and explicitly labelled **Vinnare** in mobile playoff cards.
- Penalty shootout scores and lottery decisions are shown below the relevant mobile match.
- The bronze match is no longer hidden on screens below 680 px; it is rendered outside the desktop-only scroll container.
- Bronze-match team names now resolve to the actual teams when known, and its winner/decider is highlighted consistently.
- No additional database queries were introduced; the existing bracket/team snapshot is reused.
