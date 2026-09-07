# CupNavi v478 — Playoff Chain Audit

v475–v477 skyddade direkta slutspelsberoenden. v478 går igenom hela kedjan.

Exempel:
kvartsfinal → semifinal → final

Om ett resultat i kvartsfinalen ändras kan CupNavi nu kontrollera både semifinal och final, inklusive förlorargrenar som bronsmatch.

Teknik:
- alla matcher i samma bracket läses i en sammanhållen snapshot,
- winner:/loser:-referenser traverseras rekursivt,
- traversal är cykelsäker,
- endast verkliga descendants bedöms,
- befintlig lock-/guidance-/recoverylogik återanvänds.

Ingen schemaändring. Schema v32.
