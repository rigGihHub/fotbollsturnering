# CupNavi QUALITY V100

Version: 2026.08.24-100-INTERNATIONAL-CORE

## Scope
- Architecture milestone for international, multisport growth rather than a feature burst.
- Added canonical language-independent sport IDs and participant types in `cupnavi_core/sports.py`.
- Existing Swedish sport names remain backward compatible.
- Added locale/timezone primitives in `cupnavi_core/i18n.py`.
- Added generic role/permission primitives in `cupnavi_core/permissions.py`.
- Schema v7 adds tournament locale, IANA timezone, participant type and country code.
- Admin overview can save language/region, timezone and country code.
- Existing Streamlit UI, v90 performance behavior and v99 Team Portal remain intact.
- No destructive table/column rename; `teams` is retained for compatibility while new domain code can reason in participants.

## Architectural direction
- New domain code should depend on canonical sport IDs, participant types and permissions rather than Swedish UI labels.
- Future extraction from `app.py` should be incremental and covered by regression tests.
- Streamlit remains the delivery shell; the extracted core is kept UI-independent so it can support a future API/web frontend if needed.

## Verification
- Python syntax compilation: PASS.
- Full pytest suite: PASS — 205 tests.
- Schema migration target: v7.
- Regression coverage added for canonical sports, locales/timezones, permissions and international schema fields.
