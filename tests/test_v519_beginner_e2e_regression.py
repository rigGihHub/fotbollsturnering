from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
FLOW = (ROOT / "cupnavi_core" / "planning_flow_nav.py").read_text(encoding="utf-8")
SCHEDULE = (ROOT / "cupnavi_core" / "schedule_workspace_view.py").read_text(encoding="utf-8")
PUBLICATION = (ROOT / "cupnavi_core" / "admin_publication_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_version_is_synced():
    assert VERSION == "2026.09.07-519-BEGINNER-E2E-REGRESSION"
    assert f'APP_BUILD_VERSION = "{VERSION}"' in APP
    assert VERSION in (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")


def test_beginner_journey_has_one_canonical_seven_step_contract():
    assert 'FLOW_STEPS = ["Cupinfo", "Lag", "Grupper", "Planer & tider", "Schema", "Kontroll", "Publicera"]' in FLOW
    assert "Din väg till publicerad cup" in APP
    assert "_ADMIN_FLOW_STEPS" not in APP


def test_new_cup_can_start_manually_or_from_existing_program():
    assert '"Fortsätt med Cupinfo →"' in APP
    assert 'args=("Cupinställningar",)' in APP
    assert '"Läs in foto/PDF →"' in APP
    assert 'args=("Import",)' in APP


def test_journey_does_not_skip_pitches_before_schedule():
    assert '"Fortsätt till Planer & tider →"' in APP
    assert 'key=f"v514_groups_to_pitches_{tid}"' in APP
    assert '"Planer & tider": "Cupinställningar"' in FLOW
    assert '"Schema": "Skapa och publicera schema"' in FLOW


def test_imported_or_existing_schedule_is_editable_but_not_silently_rebuilt():
    assert "Redigera befintligt schema manuellt" in SCHEDULE
    assert "_regenerating_unplayed_schedule" in SCHEDULE
    assert "_confirm_regenerate = st.checkbox(" in SCHEDULE
    assert "_schedule_action_disabled = _regenerating_unplayed_schedule and not _confirm_regenerate" in SCHEDULE


def test_schedule_can_always_continue_to_control():
    assert '"Fortsätt till Kontroll →"' in SCHEDULE
    assert 'current_step="Kontroll"' in APP


def test_control_routes_blockers_and_separates_publish_step():
    assert '"Fortsätt till Publicera →"' in APP
    assert 'current_step="Publicera"' in APP
    assert "Steg 7 av 7 · Publicera" in PUBLICATION
    assert "Publicering är blockerad" in PUBLICATION


def test_setup_remains_reachable_after_creation():
    assert '"⚙️ Ändra cupsetup"' in APP
    assert "new_tournament_setup_mode" in APP
    assert '"edit"' in APP
