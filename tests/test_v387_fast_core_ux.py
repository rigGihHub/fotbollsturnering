from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
SCHEDULE=(ROOT/"cupnavi_core/schedule_workspace_view.py").read_text(encoding="utf-8")
RESULTS=(ROOT/"cupnavi_core/admin_results_view.py").read_text(encoding="utf-8")
VERSION=(ROOT/"VERSION.txt").read_text().strip()

def _lag_block():
    start=APP.index('if admin_page == "Lag":')
    end=APP.index('if admin_page == "Grupper":',start)
    return APP[start:end]

def test_release_version():
    assert VERSION=="2026.09.03-424-PUBLIC-INFO-ROUNDTRIP-CUT"

def test_team_secondary_tools_are_true_lazy_gates():
    lag=_lag_block()
    for key in (
        "lag_ai_roster_upload_",
        "lazy_team_tools_",
        "lazy_team_checkin_",
        "lazy_team_codes_",
        "lazy_team_messages_",
        "lazy_team_edit_",
    ):
        assert key in lag
    assert 'with st.expander("Lagportal – koder", expanded=False):' not in lag
    assert 'with st.expander("Redigera eller ta bort lag", expanded=False):' not in lag

def test_schedule_heavy_detail_block_is_lazy():
    assert "show_schedule_detail_tools = st.toggle(" in SCHEDULE
    gate=SCHEDULE.index("show_schedule_detail_tools = st.toggle(")
    query=SCHEDULE.index("adjustable_matches = all_rows(", gate)
    assert SCHEDULE.index("if show_schedule_detail_tools:", gate) < query
    assert '"Visa detaljer och redigering"' in SCHEDULE

def test_result_editor_defaults_to_pending_matches():
    assert '"Att rapportera", "Alla matcher"' in RESULTS
    assert 'pending_result_matches = [' in RESULTS
    assert 'editor_matches = pending_result_matches if result_scope == "Att rapportera" else playable_matches' in RESULTS
    assert "for match_row in editor_matches:" in RESULTS

def test_result_editor_prepares_updates_only_for_visible_scope():
    assert "playable_matches=editor_matches" in RESULTS
    assert 'if editor_matches:' in RESULTS
