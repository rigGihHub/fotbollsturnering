from pathlib import Path


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def test_ux2_design_system_and_mobile_nav_present():
    text = app_text()
    assert "def inject_ux2_css():" in text
    assert "cn-mobile-bottom-nav" in text
    assert "min-height:44px" in text
    assert "cn-progress-hero" in text


def test_admin_information_architecture_is_reduced():
    text = app_text()
    for label in ("Översikt", "Deltagare", "Matcher", "Organisation", "Kommunikation"):
        assert label in text

def test_public_views_use_friendly_error_boundary():
    text = app_text()
    assert "def _render_with_friendly_error" in text
    assert "Fel-ID:" in text
    assert "human_error_id" in text

def test_schedule_has_visual_board():
    text = app_text()
    assert "🗓️ Visuellt schema" in text
    assert "schedule_board(" in text
    assert "cn-match-tile" in text

def test_onboarding_has_recommendation_card():
    text = app_text()
    assert "CupNavi rekommenderar" in text
    assert "cn-recommend-card" in text

def test_command_palette_shortcut_exists():
    text = app_text()
    assert "ctrlKey||e.metaKey" in text
    assert "key.toLowerCase()==='k'" in text


def test_ux2_empty_states_and_undo_exist():
    text = app_text()
    assert "def render_empty_state" in text
    assert "↶ Ångra" in text
    assert "ux2_schedule_undo_" in text
