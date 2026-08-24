# CupNavi QUALITY V106

Version: 2026.08.24-106-TEAM-PRIVACY

## Scope
- Login forms disappear immediately after successful authentication in Admin and Match reporter; Team portal already reruns after authentication.
- Admin team page shows a clear table of all team access codes. Legacy hash-only codes can be explicitly replaced in bulk with displayable codes.
- Responsible team contact fields added and visible to Admin; contacts can be protected from public display.
- Team portal player entry now requires first name, last name and birth year.
- Players can be marked protected; protected names are masked in public statistics while remaining visible to authorized roles.
- Database schema upgraded to v9.

## Verification
- Python syntax compilation: PASS.
- Full pytest suite: PASS — 234 tests.
- Regression tests added in tests/test_team_privacy_v106.py.
