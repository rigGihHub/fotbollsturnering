from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text()
WIZ=(ROOT/"cupnavi_core/new_tournament_wizard.py").read_text()
SETUP=(ROOT/"cupnavi_core/initial_setup_view.py").read_text()
MIG=(ROOT/"cupnavi_core/migrations.py").read_text()

def test_release_version():
    assert (ROOT/"VERSION.txt").read_text().strip()=="2026.09.04-449-MOBILE-PLAYOFF-ACTION"

def test_wizard_travel_uses_only_buffer_and_auto_route_action():
    assert "Ta hänsyn till restid mellan planerna" in WIZ
    assert "Extra tid utöver den faktiska restiden" in WIZ
    assert "Beräkna restider med CupNavi" in WIZ
    assert "calculate_pitch_travel_times" in WIZ

def test_google_routes_is_server_side_and_buffer_is_persisted():
    assert "routes.googleapis.com/directions/v2:computeRoutes" in APP
    assert 'st.secrets.get("GOOGLE_MAPS_API_KEY"' in APP
    assert "pitch_travel_buffer_minutes" in MIG
    assert "LATEST_SCHEMA_VERSION = 32" in MIG

def test_manual_path_goes_directly_to_dedicated_rules_block():
    assert 'st.session_state["new_tournament_setup_mode"] = "rules"' in WIZ
    assert 'if st.session_state.get("new_tournament_setup_mode") == "rules"' in SETUP
    assert 'st.markdown("## Tävlingsregler")' in SETUP
    assert '"← Tillbaka till upplägg"' in SETUP

def test_cupnavi_suggestion_has_explicit_button():
    assert '"Visa CupNavis förslag"' in WIZ
    assert 'wizard_rec_visible_' in WIZ
