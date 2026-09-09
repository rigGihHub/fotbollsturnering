# CupNavi v436 – Schedule validation fast path

## Why
Schema was still doing duplicate work on every rerun even after the broader admin caching work. The admin shell had already loaded `schedule_rules` and already computed/cached `validate_schedule`, but the Schema workspace fetched the rules again and ran the full validation again. A collapsed per-group expander also executed two aggregate queries despite not being opened.

## Changes
- Reuse the admin shell `schedule_rules` snapshot on Schema.
- Reuse the already invalidated/cached schedule validation snapshot instead of re-running the full conflict/rest analysis.
- Skip validation entirely when no scheduled matches exist.
- Make per-group details truly opt-in with a toggle, so its aggregate queries run only when requested.
- No schedule generation, publication, validation or sports rules were weakened or removed.

## Expected effect
Faster Schema page entry, faster widget reruns, fewer Turso roundtrips and less repeated CPU work, especially on larger cups.
