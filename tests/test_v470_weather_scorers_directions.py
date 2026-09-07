from pathlib import Path

VERSION = "2026.09.07-500-MULTI-DOCUMENT-IMPORT"
APP = Path("app.py").read_text(encoding="utf-8")
VIEW = Path("cupnavi_core/public_team_follow_view.py").read_text(encoding="utf-8")
MATCHES = Path("cupnavi_core/public_matches_view.py").read_text(encoding="utf-8")
FILTERS = Path("cupnavi_core/public_match_filters_view.py").read_text(encoding="utf-8")


def test_version_is_v470():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_weather_defaults_on_and_is_easy_to_reach():
    assert '"🌦️ Väder för nästa match"' in VIEW
    assert 'st.session_state[f"public_matches_weather_{tournament_id}"] = True' in VIEW
    assert '"🌦️ " + tr("Visa väderprognos")' in FILTERS
    assert "value=True" in FILTERS


def test_latest_result_has_direct_scorer_action():
    assert '"⚽ Visa målskyttar och kort"' in VIEW
    assert 'st.query_params["match"] = str(_last_match_id)' in VIEW
    assert "if requested_match_id:" in MATCHES
    assert "show_match_events = True" in MATCHES
    assert '"⚽ Målskyttar och kort"' in FILTERS


def test_family_directions_are_lazy():
    start = VIEW.index('_show_family_directions = st.toggle(')
    end = VIEW.index('st.markdown("**Mina lag · kommande**")', start)
    block = VIEW[start:end]
    assert "if _show_family_directions:" in block
    assert "SELECT label,url FROM venue_points" in block
    assert "st.link_button(" in block
    assert '"📍 Öppna vägbeskrivning' in block


def test_existing_single_team_directions_still_exist():
    assert "show_directions = st.toggle(" in VIEW
    assert "if show_directions:" in VIEW
    assert '"📍 Vägbeskrivning till' in VIEW


def test_no_weather_network_call_added_to_team_follow_first_paint():
    assert "fetch_weather_forecast(" not in VIEW
    assert "weather_for_match(" not in VIEW
