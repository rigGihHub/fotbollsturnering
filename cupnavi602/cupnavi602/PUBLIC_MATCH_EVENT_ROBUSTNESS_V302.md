# CupNavi v302 – Public match event robustness

Hardened the public match-event presentation boundary so nullable persisted player/team names are normalized before HTML escaping. This prevents a TypeError in public match cards while preserving protected-player handling, event ordering, and goals/red-card semantics. No schema, schedule, auth, publication, or write-path changes.
