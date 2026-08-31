# Public pre-route fast path v321

## Problem
Every public navigation click reruns the Streamlit script. Before the public workspace was rendered, CupNavi injected a large CSS payload that primarily targets BaseWeb date inputs/calendars used by admin/setup forms. The same markdown block also contained public legacy polish, so the entire payload was rendered in tournament view even though the calendar rules were irrelevant there.

## Change
The legacy CSS payload is now split by view mode:
- Tournament view renders only shared readability rules and the existing public legacy polish.
- Admin, team portal and match reporter retain the existing calendar/date-picker override and shared readability rules.

No public navigation, tournament lookup, data loading, authentication, scheduling, result, playoff or persistence behavior changed.

## Expected effect
Public reruns send/render less irrelevant CSS before `render_public_view()`, reducing pre-route work on every main-menu click. This complements v315-v320, which reduced navigation, data, team-follow, statistics and playoff costs inside the public workspace.

## Limitation
This is a static/runtime-path optimization. Actual perceived latency still needs live browser verification after deployment.
