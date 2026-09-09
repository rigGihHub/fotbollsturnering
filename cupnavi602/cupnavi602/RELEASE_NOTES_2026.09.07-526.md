# CupNavi v526 – Shell tournament cache

Performance-only iteration.

- Reuses one short-lived tournament-list snapshot for the Admin shell and clone picker.
- Removes one overlapping Turso tournament-list roundtrip from normal Admin reruns.
- Caches generic public tournament discovery briefly across rapid reruns.
- Invalidates shell/public tournament caches immediately through the normal write path.
- No product features or UI changes.
