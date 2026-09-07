# CupNavi v476 — Playoff Correction Guidance

När en tidigare slutspelsmatch inte får korrigeras eftersom en senare beroende match redan används visar CupNavi nu vilken senare match som låser ändringen.

Guidningen innehåller:
- slutspelssteg och matchnummer,
- internt match-ID,
- om matchen har startat,
- om resultat finns,
- om matchhändelser finns,
- avsparkstid när den finns,
- tydlig instruktion att återställa eller rätta den senare matchen först.

Matchrapportörens bulkflöde visar första konkreta blockeringen.
Schema/admin-flödet visar upp till tre konkreta beroenden.

Ingen automatisk omskrivning av senare matcher görs.
Ingen schemaändring. Schema v32.
