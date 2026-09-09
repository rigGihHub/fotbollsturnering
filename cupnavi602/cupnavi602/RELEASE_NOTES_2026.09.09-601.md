# CupNavi v601 – Kit search accuracy + speed

Focus: make the new shirt/kit finder both faster and more trustworthy.

## Search
- One broader multi-source pass is the normal path.
- Targeted second pass only when needed.
- Parallel whole-cup scan (max 4 workers).
- 12h process cache for identical searches.

## Accuracy
- Home and away verification are source-specific.
- A model boolean alone can no longer mark a kit verified.
- Evidence and sources are exposed per kit.
- Current season and primary/official sources are explicitly prioritised.

## Safety
- Unverified kit colours remain editable suggestions only.
- Explicit organiser approval is still required before persistence.
