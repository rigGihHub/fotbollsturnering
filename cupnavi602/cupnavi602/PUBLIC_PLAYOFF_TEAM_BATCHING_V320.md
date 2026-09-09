# CupNavi v320 – Public playoff team batching

The public playoff renderer now reuses the compact team snapshot already loaded by the public workspace.

## Why
Previously each displayed bracket loaded all tournament teams again before rendering names and kit colors. A tournament with both A- and B-playoffs could therefore repeat the same team query once per bracket on every playoff render.

## Change
- `render_public_statistics_section` receives the public `team_by_id` mapping.
- Public bracket rendering passes that mapping into `render_bracket_tree`.
- `render_bracket_tree` uses the injected mapping when available.
- Admin/standalone rendering keeps a database fallback.
- The fallback query is narrowed to `id,name,primary_color,secondary_color`.

No bracket generation, source resolution, result, winner, schedule or concurrency logic changed.
