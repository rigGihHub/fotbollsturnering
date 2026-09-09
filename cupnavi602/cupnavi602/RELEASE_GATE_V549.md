# CupNavi v549 — Current Release Gate

CupNavi retains a large historical regression archive. Many release-specific
files intentionally assert the exact version/UI source that existed when that
release was built. Running every historical contract against the newest source
therefore produces false failures mixed with useful regressions.

v549 does **not** delete or rewrite those historical tests. Instead it adds a
current release gate:

```bash
python scripts/run_current_release_gate.py
```

The gate compiles the app/core, runs all non-release-specific tests, then runs a
curated set of recent functional/safety contracts covering schedule repair,
public highlights, actionable schedule errors, reporter correction/push safety,
setup-driven reporter controls, big mobile score controls, and network/write
resilience.

One legacy test is explicitly deselected: the v90 weather test requires weather
to default ON. Since v528 weather is intentionally opt-in to protect public
first-paint performance. v549 adds a current test asserting the opt-in contract.

A separate real v548 defect was also fixed: VERSION.txt/app.py had advanced to
v548 while cupnavi_core/version.py still reported v547. v549 synchronizes all
three release identifiers.
