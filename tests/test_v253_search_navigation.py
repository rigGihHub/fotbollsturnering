
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")

def test_search_hit_carries_context_into_destination():
    assert "def _open_admin_search_hit(target_page, kind, entity_id, team_id=None):" in APP
    assert 'st.session_state[admin_page_key] = target_page' in APP
    assert 'st.session_state[f"admin_search_focus_entity_{tid}"] = int(entity_id)' in APP
    assert 'st.session_state[f"global_admin_search_{tid}"] = ""' in APP

def test_player_search_contains_team_id_and_routes_to_rosters():
    search=APP[APP.index('with st.expander("Sök i cupen"'):APP.index("admin_page = st.session_state[admin_page_key]")]
    assert "players.team_id" in search
    assert '"target_page": "Trupper"' in search
    assert '"team_id": int(row["team_id"])' in search

def test_roster_page_auto_selects_player_team():
    roster=APP[APP.index('if admin_page == "Trupper":'):APP.index('if admin_page == "Domare":')]
    assert '_focus_team_id = st.session_state.get(f"admin_search_focus_team_{tid}")' in roster
    assert 'st.session_state[_roster_selector_key] = int(_focus_team_id)' in roster
    assert "Öppnad från sökningen" in roster

def test_team_referee_and_match_search_targets_show_context():
    assert 'if _search_focus_kind == "Lag"' in APP
    assert 'if _focus_kind == "Domare"' in APP
    assert 'if _focus_kind == "Match"' in APP
    assert "Öppnad från Sök i cupen" in APP
