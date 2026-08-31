from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SETUP=(ROOT/"cupnavi_core"/"initial_setup_view.py").read_text(encoding="utf-8")
APP=(ROOT/"app.py").read_text(encoding="utf-8")
VERSION=(ROOT/"VERSION.txt").read_text().strip()

def test_version():
    assert VERSION=="2026.08.31-353-GROUP-FLOW-PITCH-TIMING"
    assert VERSION in APP

def test_technical_editability_table_is_removed():
    assert "### 7. Kontroll & skapa" not in SETUP
    assert "_editability = pd.DataFrame" not in SETUP
    assert "### 7. Redo att fortsätta" in SETUP

def test_final_setup_shows_only_actionable_readiness_checks():
    assert "_setup_completion_checks" in SETUP
    assert '"Åldersklass / kategori"' in SETUP
    assert '"Planer och speltider"' in SETUP
    assert '"Planadresser"' in SETUP
    assert '"Tävlingsläge"' in SETUP
    assert "Rätta punkterna ovan" in SETUP

def test_handoff_explains_the_rest_of_the_journey():
    assert "Lägg till lag → Grupper → Schema → Kontroll → Publicera." in SETUP
    assert 'key=f"v351_setup_to_teams_{tournament_id}"' in SETUP
    assert 'st.session_state[f"admin_page_{tournament_id}"] = "Lag"' in SETUP

def test_optional_statistics_are_before_final_handoff_and_collapsed():
    stats=SETUP.index('with st.expander("Valfria statistik- och driftfunktioner"')
    finish=SETUP.index('st.markdown("### 7. Redo att fortsätta")')
    assert stats < finish
    assert 'expanded=False' in SETUP[stats:finish]

def test_standard_path_keeps_single_existing_fast_track_cta():
    assert '_setup_ready = _fast_track_ready' in SETUP
    assert 'if _show_advanced_setup:' in SETUP
    assert SETUP.count('"Fortsätt → Lägg till lag"') >= 2
