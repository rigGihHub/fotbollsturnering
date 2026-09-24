#!/usr/bin/env python3
"""Run the maintained CupNavi release gate without historical version pins.

The legacy gate contains a curated list of still-useful functional contracts.
This runner preserves that list, but fixes discovery so files whose names carry
an old release suffix (for example *_v653.py) are not accidentally treated as
evergreen tests. Explicit historical source/version-pin tests superseded by the
current owner admin flow are also removed from the curated list.
"""
from __future__ import annotations

import ast
import compileall
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
LEGACY_GATE = ROOT / "scripts" / "run_current_release_gate.py"

RELEASE_SUFFIX = re.compile(r"_v\d+(?:_|\.py$)")
SUPERSEDED_RECENT_FILES = {
    "tests/test_admin_login_diagnostics_v653.py",
    "tests/test_owner_cup_trash_v655.py",
    # Exact source formatting/layout contracts replaced by the retrying API
    # client and the newer wrapping mobile team-row implementation.
    "tests/test_v613_next_frontend_foundation.py::test_public_api_is_used",
    "tests/test_v615_next_visual_runtime_hardening.py::test_matchday_hero_search_is_not_limited_to_first_18",
}
SUPERSEDED_EVERGREEN_FILES = {
    # These source-text tests target the pre-shell admin page and the retired
    # first-generation import launcher. Their behavior is covered by the
    # active admin shell, resilient launcher and browser/build gates.
    "test_current_admin_api_wake_guard.py",
    "test_current_document_import_completion_summary.py",
    "test_current_next_initial_schedule_import.py",
    "test_current_next_photo_import_parity.py",
    "test_current_next_playoff_import.py",
    "test_current_owner_cup_management.py",
}


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def curated_recent_nodes() -> list[str]:
    tree = ast.parse(LEGACY_GATE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "recent_nodes" for target in node.targets):
            continue
        values = ast.literal_eval(node.value)
        return [
            item for item in values
            if item not in SUPERSEDED_RECENT_FILES and item.split("::", 1)[0] not in SUPERSEDED_RECENT_FILES
        ]
    raise RuntimeError("recent_nodes saknas i legacy release gate")


def is_evergreen(path: Path) -> bool:
    name = path.name
    if name in SUPERSEDED_EVERGREEN_FILES:
        return False
    if name.startswith("test_v") or name.startswith("test_current_release_gate_v"):
        return False
    if RELEASE_SUFFIX.search(name):
        return False
    return True


def main() -> int:
    if not compileall.compile_dir(ROOT / "cupnavi_core", quiet=1):
        return 1
    if not compileall.compile_dir(ROOT / "cupnavi_api", quiet=1):
        return 1
    if not compileall.compile_file(ROOT / "app.py", quiet=1):
        return 1

    evergreen = sorted(
        str(path.relative_to(ROOT))
        for path in TESTS.glob("test_*.py")
        if is_evergreen(path)
    )
    if evergreen:
        run([sys.executable, "-m", "pytest", *evergreen])

    recent = curated_recent_nodes()
    if recent:
        run([sys.executable, "-m", "pytest", *recent])

    print("MAINTAINED RELEASE GATE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
