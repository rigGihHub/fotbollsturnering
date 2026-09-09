from pathlib import Path
import ast

def app_text():
    return Path("app.py").read_text(encoding="utf-8")

def test_sponsor_forms_do_not_depend_on_re_match():
    text = app_text()
    start = text.index('if admin_page == "Sponsorer":')
    end = text.index('if admin_page == "Erbjudanden":', start)
    block = text[start:end]
    assert "re.match(" not in block
    assert "normalize_website_url(sponsor_website)" in block
    assert "normalize_website_url(edit_website)" in block

def test_normalizer_uses_urlparse_and_adds_https():
    text = app_text()
    assert "def normalize_website_url(value):" in text
    assert 'candidate = value if "://" in value else f"https://{value}"' in text
    assert "urlparse(candidate)" in text

def test_urlparse_is_imported():
    tree = ast.parse(app_text())
    found = False
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "urllib.parse":
            found = any(alias.name == "urlparse" for alias in node.names)
    assert found
