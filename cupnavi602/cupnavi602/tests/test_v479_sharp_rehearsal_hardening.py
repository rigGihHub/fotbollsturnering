from pathlib import Path
from cupnavi_core.sharp_rehearsal import rehearsal_steps, build_sharp_rehearsal_verdict

VERSION = "2026.09.07-525-OPTIONAL-REFEREE-SETUP"
APP = Path("app.py").read_text(encoding="utf-8")


def test_version_is_v479():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_no_playoff_keeps_core_rehearsal_compact():
    steps = rehearsal_steps(has_playoff=False)
    assert len(steps) == 9
    assert all(not step.key.startswith("playoff") for step in steps)


def test_playoff_rehearsal_requires_dependency_chain_and_recovery():
    keys = [step.key for step in rehearsal_steps(has_playoff=True)]
    assert keys[-4:] == [
        "playoff",
        "playoff_dependency",
        "playoff_chain",
        "playoff_recovery",
    ]
    assert len(keys) == 13


def test_go_requires_all_playoff_safety_checks():
    completed = {step.key: True for step in rehearsal_steps(has_playoff=True)}
    completed["playoff_chain"] = False
    verdict = build_sharp_rehearsal_verdict(
        technical_ready=True,
        completed=completed,
        has_playoff=True,
    )
    assert verdict.approved is False
    assert verdict.required_count == 13
    assert verdict.completed_required == 12
    assert verdict.remaining[0].key == "playoff_chain"


def test_all_playoff_steps_green_allows_pass_when_technical_ready():
    completed = {step.key: True for step in rehearsal_steps(has_playoff=True)}
    verdict = build_sharp_rehearsal_verdict(
        technical_ready=True,
        completed=completed,
        has_playoff=True,
    )
    assert verdict.approved is True


def test_ui_calls_for_two_to_three_sessions():
    assert "Skarpt genrep · 2–3 mobiler/sessioner" in APP
    assert "beroendeskydd över hela slutspelskedjan är startkrav" in APP
