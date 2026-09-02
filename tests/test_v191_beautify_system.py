from pathlib import Path
from cupnavi_core.public_view_logic import public_navigation_specs
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
STYLE=(ROOT/"cupnavi_core/style_system.py").read_text(encoding="utf-8")
PWA=(ROOT/"public_pwa/styles.css").read_text(encoding="utf-8")
STATS=(ROOT/"cupnavi_core/public_statistics_view.py").read_text(encoding="utf-8")
MATCH=(ROOT/"cupnavi_core/public_match_cards.py").read_text(encoding="utf-8")
R="2026.09.02-390-PUBLIC-SHARE-TOPLIST-UX"

def test_design_system_has_functional_tokens():
    for token in (
        "--cn-primary","--cn-bg","--cn-surface","--cn-border","--cn-text",
        "--cn-success","--cn-warning","--cn-error","--cn-disabled",
        "--cn-space-1","--cn-space-8","--cn-radius-sm","--cn-radius-lg",
    ):
        assert token in STYLE

def test_design_removes_brand_gradient_and_glass():
    brand=APP[APP.index("def render_persistent_brand"):APP.index("render_persistent_brand()")]
    assert "linear-gradient" not in brand
    assert "backdrop-filter" not in brand
    assert "border-radius:999px" not in brand

def test_buttons_inputs_focus_and_reduced_motion_are_standardized():
    assert "button:focus-visible" in STYLE
    assert '[data-testid="stTextInput"] input' in STYLE
    assert "@media(prefers-reduced-motion:reduce)" in STYLE

def test_public_navigation_is_text_first_and_mobile_has_cupinfo():
    specs=public_navigation_specs()
    assert specs[0][2] == "Matcher"
    assert specs[0][3] == "Matcher"
    flat=" ".join(str(item) for spec in specs for item in spec)
    assert "🗓️" not in flat and "📊" not in flat and "🏆" not in flat

def test_key_empty_states_are_action_oriented():
    assert "def render_empty_state" in APP
    assert "Inga matcher i det här urvalet" in MATCH
    assert "När arrangören har publicerat gruppindelningen" in STATS

def test_pwa_uses_same_restrained_tokens():
    assert "--cn-primary:#176b3a" in PWA
    assert "@media(prefers-reduced-motion:reduce)" in PWA

def test_version():
    assert "release_ui_label(APP_BUILD_VERSION)" in APP
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
