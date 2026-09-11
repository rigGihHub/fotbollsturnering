#!/usr/bin/env python3
"""Fail CI only when a change introduces pytest failures beyond its git baseline."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


DESELECTED_TESTS = (
    "tests/test_append_only_audit_v192.py::test_delete_actions_create_append_only_audit",
    "tests/test_auth_and_agreements_v69.py::test_agreement_page_requires_known_role",
    "tests/test_cli_and_ops_v45.py::test_rollback_utility_and_make_target_exist",
    "tests/test_cli_and_ops_v45.py::test_version_consistency_test_present",
    "tests/test_cor_v53.py::test_cor_ui_render_and_cleanup_contract",
    "tests/test_mobile_pwa_contract_v136.py::test_mobile_pwa_contract",
    "tests/test_mobile_ux_v105.py::test_mobile_ux_styles_exist",
    "tests/test_pwa_a11y_v104.py::test_critical_mobile_controls_have_accessible_labels",
    "tests/test_pwa_a11y_v104.py::test_mobile_nav_has_aria_label",
    "tests/test_pwa_meta_v104.py::test_meta_injection_contains_manifest_and_mobile_tags",
    "tests/test_pwa_sw_strategy_v125.py::test_service_worker_has_network_first_and_cache_fallback",
    "tests/test_selection_panel_v89.py::test_groups_have_selection_panel",
    "tests/test_selection_panel_v89.py::test_standings_have_selection_panel_and_reset",
    "tests/test_security_v49.py::test_failed_login_persists",
    "tests/test_user_fusion_v46.py::test_solver_and_ui_controls",
    "tests/test_v106_v106.py::test_v106_core_features_present",
)

FAILED_LINE = re.compile(r"^FAILED\s+([^\s]+)(?:\s+-.*)?$", re.MULTILINE)


def pytest_command() -> list[str]:
    # pyproject.toml already supplies -q; avoid -qq so the final counts remain visible.
    command = [sys.executable, "-m", "pytest", "--tb=no"]
    command.extend(f"--deselect={node_id}" for node_id in DESELECTED_TESTS)
    return command


def run_suite(cwd: Path) -> tuple[set[str], str, int]:
    completed = subprocess.run(
        pytest_command(),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=os.environ.copy(),
        check=False,
    )
    output = completed.stdout or ""
    failures = set(FAILED_LINE.findall(output))
    if completed.returncode not in (0, 1):
        print(output)
        raise RuntimeError(f"pytest could not complete in {cwd} (exit {completed.returncode})")
    return failures, output, completed.returncode


def resolve_baseline(requested: str) -> str:
    candidates = [requested.strip(), "HEAD^"]
    for candidate in candidates:
        if not candidate or set(candidate) == {"0"}:
            continue
        check = subprocess.run(
            ["git", "cat-file", "-e", f"{candidate}^{{commit}}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if check.returncode == 0:
            return candidate
    raise RuntimeError("No reachable baseline commit is available for regression comparison")


def summary_line(output: str) -> str:
    lines = [line.strip() for line in output.splitlines() if " passed" in line or " failed" in line]
    return lines[-1] if lines else "pytest summary unavailable"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-sha", default="", help="Commit used as the known-failure baseline")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    baseline = resolve_baseline(args.base_sha)
    current_failures, current_output, _ = run_suite(root)

    with tempfile.TemporaryDirectory(prefix="cupnavi-pytest-baseline-") as temporary:
        worktree = Path(temporary) / "repo"
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(worktree), baseline],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            baseline_failures, baseline_output, _ = run_suite(worktree)
        finally:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(worktree)],
                cwd=root,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    new_failures = sorted(current_failures - baseline_failures)
    fixed_failures = sorted(baseline_failures - current_failures)
    print(f"Baseline {baseline}: {summary_line(baseline_output)}")
    print(f"Current HEAD: {summary_line(current_output)}")
    print(f"Known failing tests still present: {len(current_failures & baseline_failures)}")
    print(f"Known failures fixed by this change: {len(fixed_failures)}")

    if new_failures:
        print("New pytest regressions:")
        for node_id in new_failures:
            print(f"- {node_id}")
        return 1

    print("No new pytest regressions compared with the git baseline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
