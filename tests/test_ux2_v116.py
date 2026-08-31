from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def app_text():
    return (ROOT / "app.py").read_text(encoding="utf-8")

def style_text():
    return (ROOT / "cupnavi_core" / "style_system.py").read_text(encoding="utf-8")

def schedule_text():
    return (ROOT / "cupnavi_core" / "schedule_workspace_view.py").read_text(encoding="utf-8")


def test_ux2_design_system_and_mobile_nav_present():
    text = style_text()
    assert "def inject_ux2_css(st, components):" in text
    assert "cn-mobile-bottom-nav" in text
    assert "min-height:44px" in text
    assert "cn-progress-hero" in text


def test_admin_information_architecture_is_reduced():
    text = app_text()
    for label in ("Översikt", "Deltagare", "Matcher", "Organisation", "Mer"):
        assert label in text

def test_public_views_use_friendly_error_boundary():
    text = app_text()
    assert "def _render_with_friendly_error" in text
    assert "Fel-ID:" in text
    assert "safe_error_record" in text

def test_schedule_has_visual_board():
    text = schedule_text()
    assert "🗓️ Visuellt schema" in text
    assert "schedule_board(" in text
    assert "cn-match-tile" in text

def test_onboarding_start_template_is_clean_without_recommendation_card():
    text = app_text()
    start = text.index('def render_new_tournament_creator')
    end = text.index('if view_mode == "Admin":\n    st.sidebar.caption', start)
    block = text[start:end]
    assert "Startmall" in block
    assert "CupNavi rekommenderar" not in block

def test_command_palette_shortcut_exists():
    text = style_text()
    assert "ctrlKey||e.metaKey" in text
    assert "key.toLowerCase()==='k'" in text


def test_ux2_empty_states_and_undo_exist():
    text = app_text()
    schedule = schedule_text()
    assert "def render_empty_state" in text
    assert "↶ Ångra" in schedule
    assert "ux2_schedule_undo_" in schedule
