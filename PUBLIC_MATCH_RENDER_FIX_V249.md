# CupNavi v1.249 – Public Match Render Fix

## Visible bug
In played public match cards the referee HTML could appear as literal text inside a dark
code-like box, e.g. `<span class="match-referee">Domare: ...</span>`.

## Cause
The public card was rendered from an indented multiline Markdown/HTML string while
`match_events_html` injected its own complete HTML block in the middle. Markdown could
treat the indented HTML that followed that injected block as a code block rather than as
part of the card.

## Fix
- Build each public match card as one compact HTML string without Markdown-significant
  indentation between the injected match-events block and the secondary metadata.
- Build referee and weather markup separately before combining them.
- Continue using `unsafe_allow_html=True` only for the final trusted application-built
  card string.
- Escape dynamic stage, status, score, date and referee values before inserting them.

No match data, result logic, event logic, referee assignment or public filtering behavior
was changed.
