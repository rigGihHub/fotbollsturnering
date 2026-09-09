# CupNavi v602 — Kit Identity Disambiguation

## Goal
Improve kit-search correctness without slowing the normal search path.

## What changed

- Club identity is now separated from shirt evidence.
- The same first web-search roundtrip can return up to four plausible club candidates when a team name is ambiguous.
- Ambiguous identity is a hard safety boundary: CupNavi does not expose or verify shirt colours until the organiser has selected the correct club.
- Candidate choices show club name, location/country, evidence source and a short reason.
- After a candidate is selected, the targeted kit search receives the chosen club identity and source URL explicitly.
- Selected identity is included in the cache key, so results from two similarly named clubs cannot contaminate one another.
- Invalid/non-URL candidate sources are discarded and candidate lists are capped at four.

## Performance

The normal path does not add a preliminary network call. Identity resolution is requested in the same search response as the existing evidence sweep. A second search happens only when ambiguity genuinely requires the organiser to choose a club, while v601's 12-hour cache, two-pass ceiling and four-team parallel tournament scan are retained.

## Safety / correctness

When `identity_status=ambiguous`, normalized results force `found=False`, `home_verified=False` and `away_verified=False` even if a model response attempted to provide colours. This prevents evidence from multiple clubs being mixed into one kit suggestion.

## Verification

- `python -m py_compile app.py cupnavi_core/ai_kit_suggestion.py cupnavi_core/version.py`: PASS
- v602 current tests: 5/5 PASS
- evergreen suite: 302 passed, 2 intentional deselections
- current release gate: 166 passed
- current release gate overall: PASS
