# CupNavi 2026.09.08-534 – Public referenced teams

Performance-only release.

- Future-cup public first paint now transfers only teams referenced by the server-side first match batch, instead of every team in the tournament.
- Exact tournament team count is still returned in the same SQL roundtrip and used in the public summary.
- Full team loading remains the fallback whenever filters/search/team-specific flows require the complete team catalogue.
- Cup-day path intentionally keeps the complete team list to avoid degrading resolved playoff/team presentation during live use.

Validation: focused v534 SQL test against SQLite, compileall.
