from pathlib import Path

VERSION = "2026.09.07-519-BEGINNER-E2E-REGRESSION"
APP = Path("app.py").read_text(encoding="utf-8")
MATCHES = Path("cupnavi_core/public_matches_view.py").read_text(encoding="utf-8")
CARDS = Path("cupnavi_core/public_match_cards.py").read_text(encoding="utf-8")
PRESENT = Path("cupnavi_core/public_presentation_view.py").read_text(encoding="utf-8")


def test_version_is_v471():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_loaded_events_render_compact_scorer_first():
    assert "cn-match-events cn-match-events-compact" in PRESENT
    assert 'event_title = "Målskyttar"' in PRESENT
    assert 'event_title = "Målskyttar & kort"' in PRESENT
    assert ".cn-match-events-compact{" in CARDS


def test_near_weather_action_is_direct_and_opt_in():
    assert "_near_weather_match = None" in MATCHES
    assert "0 <= _minutes_to_weather <= 120" in MATCHES
    assert '"🌦️ Visa väder · match om' in MATCHES
    assert 'st.session_state[f"public_matches_weather_{tournament_id}"] = True' in MATCHES


def test_weather_network_still_not_forced_in_match_orchestration():
    assert "fetch_weather_forecast(" not in MATCHES
    assert "if show_weather:" in CARDS
    assert "fetch_weather_forecast(" in CARDS


def test_existing_event_loading_stays_lazy():
    assert "if requested_match_id:" in MATCHES
    assert "elif visible_played_match_ids and _event_details_enabled:" in MATCHES
    assert "show_match_events = False" in MATCHES
    assert "if show_match_events and visible_played_match_ids" in MATCHES
