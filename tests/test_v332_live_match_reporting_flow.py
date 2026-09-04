from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_version():
    assert VERSION == "2026.09.04-449-MOBILE-PLAYOFF-ACTION"


def test_live_flow_keeps_canonical_match_team_player_state():
    assert 'reporter_event_match_' in VIEW
    assert 'reporter_event_team_' in VIEW
    assert 'reporter_quick_event_player_' in VIEW


def test_live_flow_has_previous_next_player_controls():
    assert '← Föregående spelare' in VIEW
    assert 'Nästa spelare →' in VIEW
    assert 'st.session_state[player_widget_key] = player_ids[player_index - 1]' in VIEW
    assert 'st.session_state[player_widget_key] = player_ids[player_index + 1]' in VIEW


def test_live_flow_persists_last_event_feedback():
    assert 'reporter_quick_last_event_' in VIEW
    assert 'Senast registrerat:' in VIEW
    assert "selected_team['name']" in VIEW


def test_live_flow_reuses_existing_concurrency_boundary():
    assert 'outcome = deps.save_event_rows([update])' in VIEW
    assert 'Spelarens händelser ändrades av en annan rapportör' in VIEW
