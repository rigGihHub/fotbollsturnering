from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGIC = (ROOT / "cupnavi_core" / "public_view_logic.py").read_text(encoding="utf-8")
TEAM = (ROOT / "cupnavi_core" / "public_team_follow_view.py").read_text(encoding="utf-8")
STYLE = (ROOT / "cupnavi_core" / "style_system.py").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def test_info_is_first_and_named_info():
    from cupnavi_core.public_view_logic import public_navigation_specs
    specs = public_navigation_specs()
    assert specs[0] == ("Info", "info", "Info", "Info")
    assert [row[0] for row in specs] == ["Info", "Matcher", "Mitt lag", "Tabeller", "Slutspel"]


def test_my_team_heading_is_not_duplicated_by_selector_label():
    assert "cn-public-follow-intro" in TEAM
    assert '"Välj lag"' in TEAM
    assert '"⭐ Följ mitt lag"' not in TEAM


def test_public_summary_has_balanced_desktop_grid():
    assert "v415 — Public overview balance" in STYLE
    assert "grid-template-columns:repeat(3,minmax(0,1fr))!important" in STYLE


def test_public_overview_uses_short_session_cache():
    assert "_cupnavi_public_overview_v415_" in APP
    assert "< 15.0" in APP
