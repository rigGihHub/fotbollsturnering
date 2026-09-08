from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
PUBLIC_MATCHES = (ROOT / "cupnavi_core" / "public_matches_view.py").read_text(encoding="utf-8")
SETUP = (ROOT / "cupnavi_core" / "initial_setup_view.py").read_text(encoding="utf-8")
WIZARD = (ROOT / "cupnavi_core" / "new_tournament_wizard.py").read_text(encoding="utf-8")
CREATOR = (ROOT / "cupnavi_core" / "cup_document_creator_view.py").read_text(encoding="utf-8")
SCHEDULE = (ROOT / "cupnavi_core" / "schedule_workspace_view.py").read_text(encoding="utf-8")
VERSION = "2026.09.08-558-PUBLIC-MORE-MATCHES-AND-CODE-HUB"


def test_release_files_are_current():
    assert VERSION in APP
    assert (ROOT / "VERSION.txt").read_text().strip() == VERSION
    assert VERSION in (ROOT / "cupnavi_core" / "version.py").read_text()


def test_show_more_matches_updates_limit_then_forces_parent_app_rerun():
    assert 'if st.button(\n            f"Visa {next_batch_size} fler matcher"' in PUBLIC_MATCHES
    assert 'st.session_state[limit_key] = next_visible_count(visible_match_count, total_filtered_matches)' in PUBLIC_MATCHES
    assert 'st.rerun(scope="app")' in PUBLIC_MATCHES
    assert 'on_click=_show_more_public_matches' not in PUBLIC_MATCHES
    assert 'public_matches_more_v558_' in PUBLIC_MATCHES


def test_code_hub_has_global_admin_button():
    assert '"🔐 Administrera alla koder"' in APP
    assert 'key=f"admin_all_codes_global_{tid}"' in APP
    assert 'args=("Åtkomst & koder",)' in APP
    assert 'if admin_page == "Åtkomst & koder":' in APP
    assert 'st.header("Alla koder")' in APP


def test_v557_schedule_and_rules_fixes_are_retained():
    assert "synchronized_pitch_times INTEGER NOT NULL DEFAULT 1" in APP
    assert "Paus mellan halvlekar/perioder" in APP
    assert 'if int(edited_halves) >= 2:' in APP
    assert '_address_planning_enabled = bool(_row_value(rules, "consider_pitch_travel", 0))' in WIZARD
    assert '(not consider_travel) or not bool(_addresses_to_verify)' in SETUP
    assert '"Använd det granskade matchprogrammet som cupens schema", value=True' in CREATOR
    assert 'st.session_state[f"schedule_existing_import_prefill_{tid}"] = _structured' in APP
    assert "du behöver inte läsa in bilden igen" in SCHEDULE
