from pathlib import Path
import ast

def test_no_stale_one_helper_calls_remain():
    tree = ast.parse(Path("app.py").read_text(encoding="utf-8"))
    stale = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "one"
    ]
    assert stale == []

def test_public_match_events_uses_one_row():
    text = Path("cupnavi_core/public_presentation_view.py").read_text(encoding="utf-8")
    start = text.index("def public_match_events_html(")
    end = text.index("def public_rules_html(", start)
    block = text[start:end]
    assert 'match_row = one_row("SELECT home_source, away_source FROM matches WHERE id=?"' in block
