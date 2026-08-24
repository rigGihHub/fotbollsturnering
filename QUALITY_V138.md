# QUALITY V138

Release: `2026.08.24-138-PUBLIC-MATCHES-STABILITY`

## Fix
- Härdar den publika Match-vyn mot ofullständiga/äldre matchrader.
- Väderprognosen får aldrig krascha hela Turneringsvyn.
- Ogiltig/saknad `scheduled_start` hanteras säkert i väderlogiken.
- `referee_id` läses kompatibelt även om fält saknas i äldre data.

## Verifiering
Körs vid paketering: syntaxkontroll, full pytest-svit, versionssynk och ZIP-kontroll.
