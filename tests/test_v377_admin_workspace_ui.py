from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
SCHEDULE = (ROOT / "cupnavi_core" / "schedule_workspace_view.py").read_text(encoding="utf-8")
RESULTS = (ROOT / "cupnavi_core" / "admin_results_view.py").read_text(encoding="utf-8")
STYLE = (ROOT / "cupnavi_core" / "style_system.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_version():
    assert VERSION == "2026.09.02-388-ADMIN-CORE-FLOW-CLEANUP"


def test_lag_and_groups_use_shared_workspace_headers_without_duplicate_trails():
    lag = APP[APP.index('if admin_page == "Lag":'):APP.index('if admin_page == "Grupper":')]
    groups = APP[APP.index('if admin_page == "Grupper":'):APP.index('if admin_page == "Trupper":')]
    assert 'class="cn-workspace-head"' in lag
    assert "Steg 1 av 5 · Deltagare" in lag
    assert 'class="cn-step-trail"' not in lag
    assert 'class="cn-workspace-head"' in groups
    assert "Steg 2 av 5 · Tävlingsstruktur" in groups
    assert 'class="cn-step-trail"' not in groups


def test_schedule_uses_same_step_language_without_duplicate_trail():
    assert 'class="cn-workspace-head"' in SCHEDULE
    assert "Steg 3 av 5 · Schema" in SCHEDULE
    assert 'class="cn-step-trail"' not in SCHEDULE
    assert "Bygg spelschemat" in SCHEDULE


def test_results_header_and_progress_are_compact():
    assert 'class="cn-workspace-head"' in RESULTS
    assert 'class="cn-result-progress"' in RESULTS
    assert "Resultat registrerade" in RESULTS
    assert "cn-progress-hero" not in RESULTS


def test_no_results_mode_uses_same_header_language():
    block = APP[
        APP.index('if admin_page == "Matcher och resultat":'):
        APP.index('if admin_page == "Matchhändelser":')
    ]
    assert 'class="cn-workspace-head"' in block
    assert '<div class="title">Matcher</div>' in block


def test_shared_styles_are_mobile_aware():
    for marker in (
        ".cn-workspace-head{",
        ".cn-step-trail{",
        ".cn-workspace-card{",
        ".cn-result-progress{",
    ):
        assert marker in STYLE
    assert ".cn-workspace-head .title{font-size:1.5rem}" in STYLE
    assert ".cn-result-progress{grid-template-columns:1fr auto" in STYLE
