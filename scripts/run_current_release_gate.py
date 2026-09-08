#!/usr/bin/env python3
"""Run the CupNavi current-release verification gate.

The repository intentionally retains hundreds of release-specific historical
contract tests. Many assert an exact old VERSION.txt or exact UI source text;
they are useful archaeology, but cannot be a meaningful gate for a later
release. This runner keeps those tests intact and instead executes:

1. compileall,
2. all evergreen/non-release-specific test modules,
3. a current replacement for the one superseded weather-default contract,
4. selected recent v540-v551 functional/safety contracts (not version pins),
5. the v551 current-release contract.

A failing selected test is a release blocker. Historical tests are not deleted
or rewritten just to make the suite green.
"""
from __future__ import annotations

import compileall
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> int:
    if not compileall.compile_dir(ROOT / "cupnavi_core", quiet=1):
        print("compileall failed", file=sys.stderr)
        return 1
    if not compileall.compile_file(ROOT / "app.py", quiet=1):
        print("app.py compile failed", file=sys.stderr)
        return 1

    evergreen = sorted(
        str(path.relative_to(ROOT))
        for path in TESTS.glob("test_*.py")
        if not path.name.startswith("test_v")
        and not path.name.startswith("test_current_release_gate_v")
    )

    # v90 expected weather-on-by-default. Since v528 the deliberate performance
    # contract is opt-in weather; v549 tests the current behavior explicitly.
    deselect = [
        "--deselect=tests/test_performance_v90.py::test_weather_is_on_by_default_but_user_can_toggle_it",
    ]
    run([sys.executable, "-m", "pytest", *evergreen, *deselect])

    recent_nodes = [
        # Imported-schedule safety and public summary integrity.
        "tests/test_v540_imported_schedule_repair_and_summary_fix.py",
        # Automatic highlights, excluding the historical version pin.
        "tests/test_v541_restore_public_highlights.py::test_top_scorer_is_automatic_again",
        "tests/test_v541_restore_public_highlights.py::test_partial_server_batch_does_not_fake_team_rankings",
        # Actionable schedule errors.
        "tests/test_v543_actionable_schedule_errors.py::test_issue_match_numbers_extract_single_and_pair",
        "tests/test_v543_actionable_schedule_errors.py::test_actionable_error_cards_open_manual_editor",
        # Reporter correction/push safety.
        "tests/test_v544_mobile_reporter_grace_window.py::test_v544_goal_push_waits_and_supersedes_latest_edit",
        # Current one-screen, setup-gated and large-touch reporter behavior.
        "tests/test_v545_one_screen_mobile_match_control.py::test_v545_large_mobile_controls_and_match_identity",
        "tests/test_v546_setup_driven_reporter_controls.py::test_reporter_sections_follow_setup_flags",
        "tests/test_v546_setup_driven_reporter_controls.py::test_each_player_event_control_is_individually_gated",
        "tests/test_v546_setup_driven_reporter_controls.py::test_reporter_missing_flag_defaults_do_not_expose_optional_events",
        "tests/test_v547_big_scoreboard_reporter_ui.py::test_big_scoreboard_has_large_touch_targets",
        "tests/test_v547_big_scoreboard_reporter_ui.py::test_setup_driven_event_gates_survive_scoreboard_redesign",
        "tests/test_v547_big_scoreboard_reporter_ui.py::test_correction_window_survives_scoreboard_redesign",
        "tests/test_v548_reporter_network_resilience.py::test_reporter_has_explicit_save_states",
        "tests/test_v548_reporter_network_resilience.py::test_reporter_has_live_browser_network_probe",
        "tests/test_v548_reporter_network_resilience.py::test_uncertain_write_requires_server_refresh_not_automatic_retry",
        "tests/test_v548_reporter_network_resilience.py::test_existing_safety_contracts_are_retained",
        "tests/test_current_release_gate_v551.py",
    ]
    run([sys.executable, "-m", "pytest", *recent_nodes])
    print("CURRENT RELEASE GATE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
