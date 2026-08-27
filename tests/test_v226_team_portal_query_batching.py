
from pathlib import Path
import ast

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")


def _portal():
    tree=ast.parse(APP)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="render_team_portal")
    lines=APP.splitlines()
    return "\n".join(lines[node.lineno-1:node.end_lineno])


def test_received_messages_loaded_once_and_reused_for_unread_count():
    portal=_portal()
    assert portal.count("recipient_type='team' AND recipient_team_id=?") == 1
    assert "unread_team_count = sum(" in portal


def test_match_rosters_are_batched_for_team():
    portal=_portal()
    assert "roster_ids_by_match = {}" in portal
    assert "SELECT match_id,player_id" in portal
    assert "SELECT DISTINCT match_id FROM match_rosters" not in portal
    assert 'SELECT player_id FROM match_rosters WHERE match_id=? AND team_id=?' not in portal


def test_match_and_player_formatters_use_maps():
    portal=_portal()
    assert "team_match_by_id = {" in portal
    assert "team_match_by_id[int(mid)]" in portal
    assert "player_label_by_id = {" in portal
    assert "format_func=lambda pid: player_label_by_id[int(pid)]" in portal
