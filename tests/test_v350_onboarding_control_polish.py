from pathlib import Path
import sqlite3

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
SETUP=(ROOT/"cupnavi_core"/"initial_setup_view.py").read_text(encoding="utf-8")
STYLE=(ROOT/"cupnavi_core"/"style_system.py").read_text(encoding="utf-8")
PUBLIC=(ROOT/"cupnavi_core"/"public_workspace_view.py").read_text(encoding="utf-8")
MIG=(ROOT/"cupnavi_core"/"migrations.py").read_text(encoding="utf-8")
VERSION=(ROOT/"VERSION.txt").read_text().strip()

def test_version():
    assert VERSION=="2026.09.04-449-MOBILE-PLAYOFF-ACTION"
    assert VERSION in APP

def test_new_cup_becomes_active_via_pending_selector_before_widget():
    creation=APP[APP.index("def render_new_tournament_creator"):APP.index("if view_mode == \"Admin\":\n    st.sidebar.caption")]
    assert 'st.session_state["pending_new_tournament_id"]' in creation
    selector=APP[APP.index("tournament_ids ="):APP.index('tid = st.sidebar.selectbox(')]
    assert 'st.session_state["active_tournament_selector"] = int(_pending_new_tournament_id)' in selector
    assert 'st.session_state["main_active_tournament_selector"] = int(_pending_new_tournament_id)' in selector

def test_google_maps_verification_is_required_for_entered_pitch_addresses():
    assert "Öppna {clean} i Google Maps" in SETUP
    assert "Jag har kontrollerat att adressen pekar på rätt spelplats i Google Maps" in SETUP
    assert "_addresses_to_verify" in SETUP
    assert "_guided_ready = bool(class_rows) and _planned_total > 0 and valid_windows and not _addresses_to_verify" in SETUP
    assert "_fast_track_ready = bool(class_rows) and _planned_total > 0 and valid_windows and not _addresses_to_verify" in SETUP
    assert "address_verified=0" in APP

def test_user_can_reject_cupnavi_proposal_and_open_full_controls():
    assert '"Använd CupNavis förslag"' in SETUP
    assert '"Jag vill ställa in själv"' in SETUP
    assert '"Visa och ändra alla regler & format"' in SETUP

def test_result_free_mode_is_real_persisted_mode():
    assert "results_counted" in MIG
    assert "beginner_setup_modes_v350" in MIG
    assert '"Spela utan resultaträkning"' in SETUP
    assert "matchrapporteringen stängs av" in SETUP
    assert "resultat registreras inte och ingen tabell räknas" in APP
    assert "Den här cupen spelas utan resultaträkning. Därför visas ingen tabell." in PUBLIC

def test_priority_ui_explains_rank_and_compactness():
    assert "**1 = viktigast.**" in SETUP
    assert "**Aktuell rangordning**" in SETUP
    assert 'st.markdown(f"**{_rank}.** {_priority_label}")' in SETUP
    assert '"Hur kompakt ska speldagen vara?"' in SETUP
    assert '_compact_options=["Lugnare", "Balanserad", "Ganska kompakt", "Kompakt"]' in SETUP

def test_calendar_all_descendant_surfaces_forced_light():
    assert '[data-baseweb="calendar"] div' in STYLE
    assert '[data-baseweb="calendar"] td' in STYLE
    assert "background-color:#ffffff !important;" in STYLE
