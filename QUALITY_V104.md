# CupNavi QUALITY V104

Version: 2026.08.24-104-MULTISPORT-OPTIMIZER

## Scope
- Introduces `cupnavi_core.match_engine` as a language-independent multisport match/scoring model.
- Distinguishes aggregate-score sports from set-based sports and models halves, periods, quarters and sets.
- Defines sport-specific draw/overtime/shootout/statistics/discipline capabilities.
- Introduces `cupnavi_core.schedule_optimizer` with OR-Tools CP-SAT scheduling-wave optimization and deterministic greedy fallback.
- Existing scheduler remains authoritative for exact times, pitches, locked matches, referees, travel preferences and playoff dependencies.
- OR-Tools added as a runtime dependency.
- No database schema migration in this release.

## Verification
- Python syntax compilation: PASS.
- Full pytest suite: PASS — 224 tests.
- New regression/domain tests: `tests/test_multisport_engine_v104.py`.
- NOTE: The build environment has no outbound package access, so the OR-Tools package could not be installed here. The fallback path is runtime-tested; the CP-SAT path is syntax/static-checked and will activate in deployments where requirements are installed normally.
