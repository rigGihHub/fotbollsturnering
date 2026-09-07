from pathlib import Path

VERSION = "2026.09.07-502-GUIDED-ADMIN-FLOW"
APP = Path("app.py").read_text(encoding="utf-8")
THEME = Path("cupnavi_core/texttv330_theme.py").read_text(encoding="utf-8")


def test_version_is_v488():
    assert Path("VERSION.txt").read_text().strip() == VERSION
    assert VERSION in APP


def test_texttv_foundation_is_present():
    assert "TEXT-TV 330 FUTURE FOUNDATION V488" in THEME
    assert "--cn-tt-bg:#07110c" in THEME
    assert "--cn-tt-cyan:#65e7ff" in THEME
    assert "--cn-tt-yellow:#ffe66d" in THEME
    assert "--cn-tt-green:#79ff9b" in THEME


def test_theme_is_injected_after_public_base_css():
    assert "texttv330_public_style_tag" in APP
    public_base = APP.index('if view_mode == "Turneringsvy":')
    theme_call = APP.index("texttv330_public_style_tag()", public_base)
    assert public_base < theme_call


def test_cupday_control_room_style_is_present():
    assert "V488 · Text-TV 330 meets future — Cupday control room" in THEME
    assert ".cn-day-kpi.is-live .value{color:#79ff9b!important}" in THEME
    assert "texttv330_cupday_style_tag()" in APP


def test_visual_foundation_adds_no_external_assets():
    assert "@import" not in THEME
    assert "url(" not in THEME
    assert "<script" not in THEME.lower()


def test_touch_target_contract_remains():
    assert "min-height:44px" in THEME


def test_app_monolith_stays_below_existing_budget():
    assert len(APP.splitlines()) < 16629
