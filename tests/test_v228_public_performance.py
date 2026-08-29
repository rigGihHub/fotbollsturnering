
from pathlib import Path
import ast

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
SCREEN=(ROOT/"cupnavi_core"/"public_shell_view.py").read_text(encoding="utf-8")


def _fn(name):
    tree=ast.parse(APP)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    lines=APP.splitlines()
    return "\n".join(lines[node.lineno-1:node.end_lineno])


def test_screen_tables_use_batched_all_group_tables():
    public=_fn("render_public_view")
    assert "render_public_screen_mode(" in public
    assert "table_bundle = calculate_all_group_tables(" in SCREEN
    screen_block=SCREEN[SCREEN.index("table_bundle = calculate_all_group_tables"):SCREEN.index("sponsors = all_rows",SCREEN.index("table_bundle = calculate_all_group_tables"))]
    assert "calculate_table(" not in screen_block


def test_public_bracket_preloads_team_rows_once():
    bracket=_fn("render_bracket_tree")
    assert "bracket_team_rows = all_rows(" in bracket
    assert "bracket_team_by_id = {" in bracket
    assert "home = bracket_team_by_id.get(" in bracket
    assert "away = bracket_team_by_id.get(" in bracket
    assert "home = team(home_id)" not in bracket
    assert "away = team(away_id)" not in bracket


def test_bracket_source_label_only_used_when_team_not_resolved():
    bracket=_fn("render_bracket_tree")
    assert 'home["name"] if home is not None else source_label' in bracket
    assert 'away["name"] if away is not None else source_label' in bracket
