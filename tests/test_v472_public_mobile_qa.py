from pathlib import Path

VERSION = "2026.09.07-502-GUIDED-ADMIN-FLOW"
APP = Path("app.py").read_text(encoding="utf-8")
FOLLOW = Path("cupnavi_core/public_team_follow_view.py").read_text(encoding="utf-8")
MATCHES = Path("cupnavi_core/public_matches_view.py").read_text(encoding="utf-8")
FILTERS = Path("cupnavi_core/public_match_filters_view.py").read_text(encoding="utf-8")


def test_version_is_v472():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_secondary_team_actions_are_collapsed():
    assert 'with st.expander("Mer om senaste resultatet", expanded=False):' in FOLLOW
    assert 'with st.expander("Väder & vägbeskrivning", expanded=False):' in FOLLOW
    assert '"⚽ Visa målskyttar och kort"' in FOLLOW
    assert '"🌦️ Väder för nästa match"' in FOLLOW
    assert "show_directions = st.toggle(" in FOLLOW


def test_primary_next_match_action_remains_outside_secondary_expander():
    primary = FOLLOW.index("_primary_match_action =")
    secondary = FOLLOW.index('with st.expander("Väder & vägbeskrivning"')
    assert primary < secondary
    block = FOLLOW[primary:secondary]
    assert "type=\"primary\"" in block


def test_match_event_toggle_is_hidden_when_no_played_matches():
    assert "elif visible_played_match_ids and _event_details_enabled:" in MATCHES
    assert "show_match_events = False" in MATCHES
    assert '"⚽ Målskyttar och kort"' in FILTERS


def test_exact_match_message_is_compact():
    assert 'st.caption("🔎 Exakt match")' in MATCHES
    assert 'st.info(f"🔎 Du visar match {requested_match_id}.")' not in MATCHES


def test_weather_shortcut_is_for_truly_near_matches():
    assert "0 <= _minutes_to_weather <= 120" in MATCHES
