from pathlib import Path

from cupnavi_core.public_navigation_view import build_public_navigation_html
from cupnavi_core.public_view_logic import public_navigation_specs

VERSION = "2026.09.07-493-BUTTON-LATENCY-IV"
APP = Path("app.py").read_text(encoding="utf-8")
STYLE = Path("cupnavi_core/style_system.py").read_text(encoding="utf-8")


def test_version_is_v464():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_public_nav_stays_five_core_destinations():
    specs = public_navigation_specs()
    assert len(specs) == 5
    assert [row[0] for row in specs] == ["Info", "Matcher", "Mitt lag", "Tabeller", "Slutspel"]


def test_navigation_html_has_all_destinations_without_wrapping_container():
    html = build_public_navigation_html(
        public_navigation_specs(), current_page="Matcher", public_slug="demo"
    )
    assert html.count("<a role='button'") == 5
    assert "cn-public-section-nav" in html
    assert "active" in html


def test_small_phone_breakpoints_exist():
    assert "@media(max-width:430px)" in STYLE
    assert "@media(max-width:360px)" in STYLE
    assert "@media(max-width:330px)" in STYLE


def test_small_phone_nav_keeps_touch_target_and_five_columns():
    block = STYLE[STYLE.index("@media(max-width:360px)"):STYLE.index("@media(max-width:330px)")]
    assert "min-height:44px!important" in block
    assert "font-size:8.5px!important" in block
    assert "padding-left:max(6px,env(safe-area-inset-left))!important" in block
    assert "padding-right:max(6px,env(safe-area-inset-right))!important" in block


def test_notch_and_home_indicator_safe_area_are_supported():
    assert "top:env(safe-area-inset-top,0px) !important" in STYLE
    assert "env(safe-area-inset-left)" in STYLE
    assert "env(safe-area-inset-right)" in STYLE
    assert "env(safe-area-inset-bottom)" in STYLE


def test_mobile_text_zoom_and_form_zoom_are_guarded():
    assert "-webkit-text-size-adjust:100%!important" in STYLE
    assert "text-size-adjust:100%!important" in STYLE
    assert 'input,textarea,select,[role="combobox"]{font-size:16px!important}' in STYLE


def test_mobile_media_never_overflows_viewport():
    assert "img,svg,video,canvas{max-width:100%!important;height:auto}" in STYLE
    assert "max-width:100vw!important;overflow-x:hidden!important" in STYLE
    assert "max-height:calc(100dvh - 24px)!important" in STYLE
