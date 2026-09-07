from pathlib import Path

VERSION = "2026.09.07-500-MULTI-DOCUMENT-IMPORT"
APP = Path("app.py").read_text(encoding="utf-8")
STYLE = Path("cupnavi_core/style_system.py").read_text(encoding="utf-8")


def test_version_is_v465():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_320px_navigation_does_not_fall_to_8px_text():
    block = STYLE[STYLE.index("@media(max-width:330px)"):STYLE.index("/* v465: real-phone edge cases")]
    assert "font-size:9.5px!important" in block
    assert "min-height:46px!important" in block
    assert "font-size:8px!important" not in block


def test_long_team_names_wrap_without_widening_viewport():
    assert ".cn-match-teams,.cn-match-team,.cn-match-teamline,.cn-follow-latest-result,.cn-follow-latest-result .teams{min-width:0!important;max-width:100%!important}" in STYLE
    assert "overflow-wrap:anywhere!important;word-break:break-word!important;hyphens:auto!important" in STYLE
    assert ".public-team-name{max-width:100%!important}" in STYLE


def test_landscape_short_height_has_specific_guard():
    assert "@media(orientation:landscape) and (max-height:500px) and (max-width:950px)" in STYLE
    assert "min-height:40px!important" in STYLE
    assert "padding-bottom:max(12px,env(safe-area-inset-bottom))!important" in STYLE


def test_touch_devices_keep_minimum_touch_height():
    assert "@media(pointer:coarse)" in STYLE
    assert ".cn-public-section-nav a{min-height:44px!important;touch-action:manipulation!important}" in STYLE


def test_buttons_can_wrap_instead_of_overflowing():
    assert "overflow-wrap:anywhere!important;word-break:normal!important;white-space:normal!important" in STYLE
