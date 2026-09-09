from pathlib import Path
import ast

def test_re_module_is_imported_when_re_is_used():
    text = Path("app.py").read_text(encoding="utf-8")
    tree = ast.parse(text)

    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.asname or alias.name.split(".")[0])

    assert "re." in text
    assert "re" in imported

def test_regex_sites_that_caused_production_failure_still_exist():
    text = Path("app.py").read_text(encoding="utf-8")
    assert 're.match(r"^https?://"' in text
    assert "re.sub(" in text
