# CupNavi v303 – public match event row normalization

## Root cause
The batched public event repository can receive positional tuple rows from libSQL/Turso, while the presentation layer historically assumed mapping-style rows such as sqlite3.Row. That caused a TypeError on `row["team_id"]` in production.

## Change
- Normalize event rows to named dictionaries in `fetch_public_match_events` at the repository boundary.
- Keep positional fallback for libSQL/Turso and named access for SQLite/test rows.
- Harden presentation access through the injected `row_value` helper.
- Skip malformed rows without a usable match/team id instead of crashing the public schedule.

## Scope
No write paths, schema, scheduling, results, publication, authentication or concurrency logic changed.
