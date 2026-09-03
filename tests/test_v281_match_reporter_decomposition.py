from pathlib import Path

from cupnavi_core.match_reporter_repository import (
    fetch_completed_matches,
    fetch_match_team_players,
    fetch_referee_acknowledged_match_ids,
    fetch_scheduled_matches,
)
from cupnavi_core.match_reporter_view import (
    build_event_player_rows,
    build_offline_draft_html,
    build_offline_match_options,
    build_reporter_columns,
    referee_assignment_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
REPO = (ROOT / "cupnavi_core" / "match_reporter_repository.py").read_text(encoding="utf-8")
VIEW = (ROOT / "cupnavi_core" / "match_reporter_view.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_event_projection_and_feature_columns_are_pure():
    players = [{"id": 7, "player_number": 10, "name": "Ada"}]
    existing = {7: {"goals": 2, "assists": 1, "yellow_cards": 1, "red_cards": 0}}
    rows = build_event_player_rows(players, existing)
    assert rows == [{
        "player_id": 7, "Nr": 10, "Spelare": "Ada", "Mål": 2,
        "Assist": 1, "Varningar": 1, "Utvisningar": 0,
    }]
    assert build_reporter_columns(assist_enabled=False, card_statistics_enabled=False) == ["Nr", "Spelare", "Mål"]
    assert build_reporter_columns(assist_enabled=True, card_statistics_enabled=True) == [
        "Nr", "Spelare", "Mål", "Assist", "Varningar", "Utvisningar"
    ]


def test_offline_markup_keeps_labels_as_text_and_blocks_script_termination():
    matches = [{
        "id": 4,
        "scheduled_start": "2026-08-29T09:00:00",
        "pitch_number": 2,
        "home_source": "team:1",
        "away_source": "team:2",
    }]
    options = build_offline_match_options(
        matches,
        swedish_datetime=lambda value: "29 aug 09:00",
        source_label=lambda source: "</script><b>X</b>" if source == "team:1" else "ÖSK",
    )
    html = build_offline_draft_html(options, 12)
    assert "cupnavi-offline-12" in html
    assert "<\\/script><b>X<\\/b>" in html
    assert "const matches=" in html
    assert "o.textContent=x.label" in html
    assert "</script><b>X</b>" not in html


def test_referee_assignment_markdown_escapes_dynamic_labels():
    assignment = {
        "scheduled_start": "x",
        "pitch_number": "1<script>",
        "home_source": "h",
        "away_source": "a",
    }
    text = referee_assignment_markdown(
        assignment,
        swedish_datetime=lambda value: "<time>",
        source_label=lambda source: "<AIK>" if source == "h" else "ÖSK & Co",
    )
    assert "&lt;time&gt;" in text
    assert "1&lt;script&gt;" in text
    assert "&lt;AIK&gt;" in text
    assert "ÖSK &amp; Co" in text


def test_reporter_repository_owns_read_only_sql_and_preserves_query_callback():
    calls = []
    rows = [{"id": 1}]
    def query_all(sql, params):
        calls.append((sql, params))
        return rows
    assert fetch_scheduled_matches(query_all, 3) is rows
    assert "scheduled_start IS NOT NULL" in calls[-1][0]
    assert fetch_completed_matches(query_all, 3) is rows
    assert "home_score IS NOT NULL" in calls[-1][0]


def test_roster_fallback_and_ack_set_contracts():
    calls = []
    def query_all(sql, params):
        calls.append((sql, params))
        if "JOIN match_rosters" in sql:
            return []
        if "FROM players WHERE team_id" in sql:
            return [{"id": 9}]
        if "referee_acknowledgements" in sql:
            return [{"match_id": 5}, {"match_id": 8}]
        return []
    snapshot = fetch_match_team_players(query_all, 7, 2)
    assert snapshot == {"registered": [], "players": [{"id": 9}]}
    assert fetch_referee_acknowledged_match_ids(query_all, 4, 6) == {5, 8}


def test_workspace_delegates_read_projection_and_offline_markup_while_app_keeps_writes():
    assert "fetch_scheduled_matches(deps.query_all, tournament_id)" in WORKSPACE
    assert "fetch_completed_matches(deps.query_all, tournament_id)" in WORKSPACE
    assert "build_event_player_rows(players, existing)" in WORKSPACE
    assert "build_offline_draft_html(offline_options, tournament_id)" in WORKSPACE
    assert "update_match_result_if_unchanged(" in APP
    assert "update_player_match_stats_if_unchanged(" in APP
    assert "INSERT INTO referee_acknowledgements" in APP
    assert "update_match_result_if_unchanged(" not in REPO + VIEW + WORKSPACE
    assert "update_player_match_stats_if_unchanged(" not in REPO + VIEW + WORKSPACE


def test_release_version():
    assert VERSION == "2026.09.03-424-PUBLIC-INFO-ROUNDTRIP-CUT"
