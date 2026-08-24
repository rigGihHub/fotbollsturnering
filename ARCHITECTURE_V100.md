# CupNavi V100 – international architecture direction

CupNavi is treated as an international multisport tournament platform.

## Stable boundaries
- `sports.py`: canonical sport identity and sport capabilities.
- `i18n.py`: locale/timezone primitives.
- `permissions.py`: generic roles and permissions.
- `migrations.py`: additive database evolution.
- Streamlit remains UI, not the domain model.

## Compatibility policy
Existing `teams`, Swedish labels and old cup records are not renamed destructively. New code should use participant concepts internally and map to legacy storage until a later, separately tested migration is justified.

## Next extraction targets
1. participant domain/repository
2. match domain and sport-specific scoring
3. auth/organization tenancy
4. locale-aware date/time presentation
5. notification adapters
