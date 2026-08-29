from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VIEW=(ROOT/"cupnavi_core/team_portal_view.py").read_text(encoding="utf-8")
REPO=(ROOT/"cupnavi_core/team_portal_repository.py").read_text(encoding="utf-8")

def test_team_portal_does_not_reload_players_for_match_squad():
    assert VIEW.count("players = fetch_team_players(deps.all_rows, team_id)") == 1

def test_previous_roster_lookup_is_batched():
    assert "SELECT match_id,player_id" in REPO
    assert "roster_ids_by_match = {}" in VIEW
    assert "SELECT DISTINCT match_id FROM match_rosters WHERE team_id=?" not in REPO
    assert "SELECT COUNT(*) AS n FROM match_rosters WHERE match_id=? AND team_id=?" not in REPO

def test_team_match_queries_prefilter_direct_team_sources():
    assert REPO.count("home_source=? OR away_source=?") == 1
    assert "fetch_portal_matches(" in VIEW
