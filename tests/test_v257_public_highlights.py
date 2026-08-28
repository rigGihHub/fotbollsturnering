from pathlib import Path

from cupnavi_core.public_highlights import competition_highlights, snapshot_table_bundle

APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")


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


def test_public_match_summary_places_compact_highlights_beside_metrics():
    block = APP[APP.index("_scorer_enabled = bool"):APP.index("requested_match_view =")]
    assert "cn-public-summary-row" in block
    assert "Poängledare" in block
    assert "Minst insläppta" in block
    assert "Skytteligaledare" in block
    assert "Assistledare" in block
    assert "enable_scorer_leaderboard" in block
    assert "enable_assist_leaderboard" in block


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


def test_public_highlights_do_not_reintroduce_group_db_queries_on_matches_page():
    block = APP[APP.index("_scorer_enabled = bool"):APP.index("requested_match_view =")]
    assert "snapshot_table_bundle(" in block
    assert "calculate_all_group_tables(" not in block
