# CupNavi v567 — Schema choice / novice UX

## Why
Schema mixed import, generation, editing and regeneration in one long workspace. A first-time organiser had to infer which action was safe.

## Changes
- Adds an explicit decision at the top of Schema: CupNavi creates it / I already have a schedule.
- When a schedule exists, defaults to the safe non-destructive path: keep and review.
- Existing schedules expose three explicit paths: keep/review, edit individual matches, rebuild remaining schedule.
- Regeneration is never the default and still requires a separate confirmation before unplayed times are replaced.
- Played matches/results remain protected.
- Import review only appears when the organiser chooses the existing-schedule path.
- Manual edit only appears when that path is chosen; issue actions switch to that path automatically.
- Back navigation from Schema now routes to the actual Planer & tider page.
