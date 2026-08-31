# CupNavi v323 – Public remote roundtrip fast path

## Goal
Reduce remaining public cold-load and button latency after v322 without changing tournament behavior or persistence rules.

## Changes
- Collapse the healthy schema fingerprint from five sequential DB execute calls to one read-only SQL statement using the migration marker plus critical pragma_table_info checks.
- Keep the same safe fallback: any missing/unsupported marker or column triggers the existing full bootstrap/migration path.
- Reduce source hot-deploy fingerprint work from scanning/stat-ing all cupnavi_core Python files to VERSION.txt + app.py metadata. The release process already increments VERSION.txt for every build.
- Add a 3-second public fragment query-cache epoch. Rapid navigation can reuse already loaded Turso rows, while live results/statistics are forced fresh again within a bounded window instead of remaining cached for the fragment session.

## Not changed
- Match/result persistence
- Concurrency/CAS protections
- Authentication/roles
- Schedule/playoff logic
- Public navigation semantics
- Notification subscriptions
- Visitor analytics
