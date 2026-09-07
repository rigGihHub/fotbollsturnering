from pathlib import Path

VERSION = "2026.09.07-500-MULTI-DOCUMENT-IMPORT"
APP = Path("app.py").read_text(encoding="utf-8")
REPORTER = Path("cupnavi_core/match_reporter_workspace_view.py").read_text(encoding="utf-8")
STYLE = Path("cupnavi_core/style_system.py").read_text(encoding="utf-8")


def test_version_is_v460():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_quick_score_has_keyed_mobile_shell():
    assert 'with st.container(key=f"reporter_quick_score_shell_' in REPORTER


def test_score_panel_keeps_single_rerun_callbacks():
    assert "on_click=_adjust_quick_score" in REPORTER
    assert "on_click=_save_quick_result_callback" in REPORTER
    assert "on_click=_reset_quick_score" in REPORTER


def test_reset_is_compact_but_accessible():
    assert '"↺"' in REPORTER
    assert 'help="Återställ till senast sparade resultat"' in REPORTER


def test_mobile_reporter_shell_overrides_global_column_stacking():
    assert '[class*="st-key-reporter_quick_score_shell_"]' in STYLE
    assert 'flex-wrap:nowrap!important' in STYLE
    assert 'width:auto!important' in STYLE


def test_mobile_score_remains_large_and_tappable():
    assert ".cn-reporter-score" in STYLE
    assert "font-size:1.72rem!important" in STYLE
    assert "min-height:46px!important" in STYLE


def test_simple_mode_copy_is_shorter():
    assert 'f"{len(unreported_ids)} kvar · {len(match_queue) - len(unreported_ids)} klara"' in REPORTER
    assert "Målskyttar, kort och specialfall finns i Avancerad." in REPORTER
