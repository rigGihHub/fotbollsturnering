from pathlib import Path

from cupnavi_core.sharp_rehearsal import build_sharp_rehearsal_verdict, rehearsal_steps

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.py').read_text(encoding='utf-8')
VERSION = '2026.09.07-502-GUIDED-ADMIN-FLOW'


def test_release_version():
    assert (ROOT / 'VERSION.txt').read_text(encoding='utf-8').strip() == VERSION
    assert VERSION in APP


def test_rehearsal_requires_core_live_chain_without_playoff():
    keys = [step.key for step in rehearsal_steps(has_playoff=False)]
    assert keys == ['reporter', 'public', 'goal', 'undo', 'conflict', 'network', 'finish', 'persistence', 'table']


def test_playoff_is_required_when_tournament_has_playoff_matches():
    keys = [step.key for step in rehearsal_steps(has_playoff=True)]
    assert keys[-4:] == ['playoff', 'playoff_dependency', 'playoff_chain', 'playoff_recovery']
    assert len(keys) == 13


def test_all_checks_plus_technical_ready_is_pass():
    completed = {step.key: True for step in rehearsal_steps(has_playoff=True)}
    verdict = build_sharp_rehearsal_verdict(
        technical_ready=True, completed=completed, has_playoff=True,
    )
    assert verdict.rehearsal_complete is True
    assert verdict.approved is True
    assert verdict.remaining == ()


def test_complete_rehearsal_does_not_override_technical_blocker():
    completed = {step.key: True for step in rehearsal_steps(has_playoff=False)}
    verdict = build_sharp_rehearsal_verdict(
        technical_ready=False, completed=completed, has_playoff=False,
    )
    assert verdict.rehearsal_complete is True
    assert verdict.approved is False


def test_missing_persistence_check_keeps_no_go_and_is_reported():
    completed = {step.key: True for step in rehearsal_steps(has_playoff=False)}
    completed['persistence'] = False
    verdict = build_sharp_rehearsal_verdict(
        technical_ready=True, completed=completed, has_playoff=False,
    )
    assert verdict.approved is False
    assert [step.key for step in verdict.remaining] == ['persistence']


def test_admin_ui_uses_explicit_pass_no_go_and_browser_push_not_gate():
    assert '✅ PASS · Cupen har klarat teknisk kontroll' in APP
    assert '⛔ NO-GO' in APP
    assert 'Browser-push är inte ett startkrav.' in APP
    assert 'playoff_matches' in APP
