from __future__ import annotations
from pathlib import Path
import subprocess, sys, os

ROOT=Path(__file__).resolve().parents[1]
try:
    import playwright
except ImportError:
    print("SKIP: Playwright package is not installed.")
    raise SystemExit(0)

# Check if Chromium is installed. Playwright itself gives a clear actionable error if not.
result=subprocess.run(
    [sys.executable,"-m","pytest","-q","e2e/test_mobile_pwa.py","e2e/test_reporter_reliability.py"],
    cwd=ROOT,text=True,
)
raise SystemExit(result.returncode)
