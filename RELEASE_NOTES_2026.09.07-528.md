# CupNavi v528 – Public first-paint secondary-data defer

Performance-only iteration. The public Matches page no longer enables weather forecasts or match-event details by default. Both are secondary data paths that can trigger additional remote/network work. They remain available as explicit toggles, and exact-match deep links may still show event details when appropriate.

This keeps the first public render focused on the already-loaded schedule/team snapshot and removes avoidable forecast/event work from the critical path.
