from pathlib import Path

from cupnavi_core.public_highlights import competition_highlights, snapshot_table_bundle

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
OVERVIEW=(ROOT/"cupnavi_core"/"public_match_overview.py").read_text(encoding="utf-8")
MATCHES=(ROOT/"cupnavi_core"/"public_matches_view.py").read_text(encoding="utf-8")


def _bundle():
    return {
        "groups": [{"id": 1}, {"id": 2}],
        "tables": {
            1: [
                (11, {"Lag": "Alpha", "S": 2, "GM": 5, "IM": 1, "MS": 4, "P": 6}),
                (12, {"Lag": "Beta", "S": 2, "GM": 3, "IM": 1, "MS": 2, "P": 4}),
            ],
            2: [
                (21, {"Lag": "Gamma", "S": 2, "GM": 4, "IM": 0, "MS": 4, "P": 6}),
                (22, {"Lag": "Delta", "S": 0, "GM": 0, "IM": 0, "MS": 0, "P": 0}),
            ],
        },
    }


def test_team_highlights_ignore_unplayed_teams_and_keep_point_ties():
    highlights = competition_highlights(_bundle(), [])
    assert highlights["points"] == {"names": ["Alpha", "Gamma"], "value": 6}
    assert highlights["defence"] == {"names": ["Gamma"], "value": 0}


def test_individual_leaders_follow_existing_leaderboard_tiebreaks():
    rows = [
        {"player_name": "Alex", "team_name": "Alpha", "goals": 4, "assists": 1},
        {"player_name": "Bo", "team_name": "Beta", "goals": 4, "assists": 3},
        {"player_name": "Chris", "team_name": "Gamma", "goals": 1, "assists": 5},
    ]
    highlights = competition_highlights(_bundle(), rows)
    assert highlights["scorer"] == {"player": "Bo", "team": "Beta", "value": 4}
    assert highlights["assist"] == {"player": "Chris", "team": "Gamma", "value": 5}


def test_disabled_leaderboards_are_not_exposed():
    rows = [{"player_name": "Alex", "team_name": "Alpha", "goals": 4, "assists": 5}]
    highlights = competition_highlights(_bundle(), rows, scorer_enabled=False, assist_enabled=False)
    assert "scorer" not in highlights
    assert "assist" not in highlights


def test_public_match_summary_is_compact_and_does_not_render_highlights():
    block = MATCHES[MATCHES.index("summary_html = build_summary_html("):MATCHES.index("requested_match_view =")]
    assert "build_summary_html" in block
    assert "build_highlights_html" not in block
    assert "enable_scorer_leaderboard" not in block
    assert "enable_assist_leaderboard" not in block
    assert "cn-public-summary-row" in OVERVIEW


def test_snapshot_bundle_uses_loaded_data_without_group_queries():
    teams = [
        {"id": 1, "name": "Alpha", "group_id": 7},
        {"id": 2, "name": "Beta", "group_id": 7},
    ]
    matches = [{
        "group_id": 7, "stage": "Gruppspel", "home_source": "team:1", "away_source": "team:2",
        "home_score": 2, "away_score": 0,
    }]
    bundle = snapshot_table_bundle(teams, matches)
    assert bundle["groups"] == [{"id": 7}]
    assert bundle["tables"][7][0][1]["Lag"] == "Alpha"
    assert bundle["tables"][7][0][1]["P"] == 3


def test_public_highlights_do_not_run_on_matches_page():
    block = MATCHES[MATCHES.index("summary_html = build_summary_html("):MATCHES.index("requested_match_view =")]
    assert "snapshot_table_bundle(" not in block
    assert "calculate_all_group_tables(" not in block
    assert "competition_highlights(" not in block
