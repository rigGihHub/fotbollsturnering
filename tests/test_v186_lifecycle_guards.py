from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
R="2026.08.28-252-CODE-REGEN-CONFIRM"

def test_central_environment_history_helpers_exist():
    assert "def is_test_environment" in APP
    assert "def production_history_locked" in APP
    assert "def team_has_played_result" in APP

def test_production_team_delete_is_guarded():
    assert "_team_delete_locked" in APP
    assert "Laget har ett registrerat resultat i en riktig cup" in APP
    assert "disabled=_team_delete_locked or not confirm_team_delete" in APP

def test_production_rules_are_guarded_in_ui_and_write_path():
    assert "_prod_history_locked = production_history_locked(tid, tournament)" in APP
    assert "protected_rules_changed = any([" in APP
    assert "_prod_history_locked and protected_rules_changed" in APP
    assert "Historikskyddet stoppade ändringen." in APP

def test_group_structure_is_guarded_after_play():
    assert "_group_history_locked = production_history_locked(tid, tournament)" in APP
    assert "Gruppstrukturen är låst efter första resultatet" in APP
    assert "disabled=_group_history_locked or not confirm_group_delete" in APP

def test_test_environment_is_exempt():
    assert "return (not is_test_environment(tournament_row)) and played_match_count(tournament_id) > 0" in APP

def test_version():
    assert "Version v.1.252" in APP
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
