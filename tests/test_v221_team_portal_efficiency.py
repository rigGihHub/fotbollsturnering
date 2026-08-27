from pathlib import Path
import ast

APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
TREE=ast.parse(APP)
FN=next(n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name=="render_team_portal")
BLOCK="\n".join(APP.splitlines()[FN.lineno-1:FN.end_lineno])


def test_team_portal_does_not_reload_players_for_match_squad():
    assert BLOCK.count('players = all_rows("SELECT * FROM players WHERE team_id=? ORDER BY player_number,name"') == 1


def test_previous_roster_lookup_is_batched():
    assert "SELECT match_id,player_id" in BLOCK
    assert "roster_ids_by_match = {}" in BLOCK
    assert "SELECT DISTINCT match_id FROM match_rosters WHERE team_id=?" not in BLOCK
    assert 'SELECT COUNT(*) AS n FROM match_rosters WHERE match_id=? AND team_id=?' not in BLOCK


def test_team_match_queries_prefilter_direct_team_sources():
    assert BLOCK.count("home_source=? OR away_source=?") == 2
    assert BLOCK.count('direct_team_source = f"team:{team_id}"') == 2
