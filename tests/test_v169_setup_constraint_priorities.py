from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
SETUP=(ROOT/"cupnavi_core"/"initial_setup_view.py").read_text(encoding="utf-8")
R="2026.08.31-349-BEGINNER-FIRST-RUN"

def test_release_sync():
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
    assert (ROOT/"VERSION.txt").read_text().strip()==R

def test_setup_has_constraint_model_and_priorities():
    assert "HÅRT KRAV = får aldrig brytas" in SETUP
    assert "Schemaprioriteringar" in SETUP
    assert "preference_order_json" in SETUP
    assert "Turneringens tempo" in SETUP

def test_team_requests_are_soft_ranked_preferences():
    assert "request_priority" in APP
    assert "first_match_request_penalty" in APP
    segment=APP[APP.index("while remaining:"):APP.index("# Schemalägg därefter slutspelsplatshållare")]
    assert "apply_first_match_preference(basic_start" not in segment
    assert "scheduling_candidate_key" in APP

def test_admin_owns_existing_cup_configuration():
    assert '"Cupinställningar"' in APP
    assert "Ändra cupens inställningar" in APP
    assert 'Fas: **{_phase}**' in APP

def test_sidebar_is_only_creation_groundwork():
    assert "Ny cup skapas här med bara grunduppgifter" in APP
