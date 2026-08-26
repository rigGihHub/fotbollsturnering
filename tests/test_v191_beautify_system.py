from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
PWA=(ROOT/"public_pwa/styles.css").read_text(encoding="utf-8")
R="2026.08.26-198-VISUAL-SYSTEM-CONSOLIDATION"

def test_design_system_has_functional_tokens():
    for token in (
        "--cn-primary","--cn-bg","--cn-surface","--cn-border","--cn-text",
        "--cn-success","--cn-warning","--cn-error","--cn-disabled",
        "--cn-space-1","--cn-space-8","--cn-radius-sm","--cn-radius-lg",
    ):
        assert token in APP

def test_design_removes_brand_gradient_and_glass():
    brand=APP[APP.index("def render_persistent_brand"):APP.index("render_persistent_brand()")]
    assert "linear-gradient" not in brand
    assert "backdrop-filter" not in brand
    assert "border-radius:999px" not in brand

def test_buttons_inputs_focus_and_reduced_motion_are_standardized():
    assert "button:focus-visible" in APP
    assert '[data-testid="stTextInput"] input' in APP
    assert "@media(prefers-reduced-motion:reduce)" in APP

def test_public_navigation_is_text_first_and_mobile_has_cupinfo():
    nav=APP[APP.index("main_nav = ["):APP.index("public_page = ",APP.index("main_nav = ["))]
    assert '(nav1, "Matcher", tr("Schema & resultat"))' in nav
    assert "🗓️" not in nav
    mobile=APP[APP.index("<nav class='cn-mobile-bottom-nav'"):APP.index("</nav>",APP.index("<nav class='cn-mobile-bottom-nav'"))]
    assert "section=info" in mobile
    assert "<span>Cupinfo</span>" in mobile
    assert "🗓️" not in mobile and "📊" not in mobile and "🏆" not in mobile

def test_key_empty_states_are_action_oriented():
    assert "def render_empty_state" in APP
    assert "Inga matcher i det här urvalet" in APP
    assert "När arrangören har publicerat gruppindelningen" in APP

def test_pwa_uses_same_restrained_tokens():
    assert "--cn-primary:#176b3a" in PWA
    assert "@media(prefers-reduced-motion:reduce)" in PWA

def test_version():
    assert "Version v.1.198" in APP
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
