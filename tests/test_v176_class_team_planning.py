from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
SETUP=(ROOT/"cupnavi_core"/"initial_setup_view.py").read_text(encoding="utf-8")
MIG=(ROOT/"cupnavi_core/migrations.py").read_text(encoding="utf-8")
R="2026.08.30-320-PUBLIC-PLAYOFF-TEAM-BATCHING"

def test_sidebar_no_longer_asks_global_team_count():
    start=APP.index('with st.sidebar.expander("Skapa ny turnering")')
    end=APP.index('if view_mode == "Admin":\n    clone_sources',start)
    block=APP[start:end]
    assert 'number_input("Planerat antal lag/deltagare"' not in block
    assert "Antal lag anges per tävlingsklass" in block

def test_each_class_has_planned_team_count():
    assert "planned_team_count" in APP + SETUP
    assert 'setup_class_teams_new_' in SETUP
    assert 'setup_planned_class_teams_' in SETUP
    assert "sync_expected_team_count_from_classes" in APP

def test_more_classes_allowed_until_results_exist():
    assert "_class_locked=_class_played_count > 0" in SETUP
    assert "Du kan fortfarande lägga till en klass före första spelade matchen" in SETUP
    assert "Tävlingsklasser och planerat lagantal är låsta efter att första resultatet" in SETUP

def test_global_team_limit_is_derived_from_classes():
    assert "Planerat antal lag" in APP
    assert "Beräknas från planerat antal i varje tävlingsklass" in APP
    assert "_planned_by_class=_planned_total" in SETUP

def test_migration_22_adds_class_team_count():
    assert "LATEST_SCHEMA_VERSION = " in MIG
    assert "competition_class_planned_team_count_v176" in MIG
    assert 'if migration.version == 22:' in MIG
    assert "ensure_competition_class_schema_compat(con)" in MIG

def test_release_sync():
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
    assert (ROOT/"VERSION.txt").read_text().strip()==R
