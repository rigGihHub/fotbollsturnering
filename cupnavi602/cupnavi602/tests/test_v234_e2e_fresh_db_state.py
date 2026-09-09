from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'app.py').read_text(encoding='utf-8')
E2E=(ROOT/'e2e/test_streamlit_critical_journey.py').read_text(encoding='utf-8')
def _fn(name):
    tree=ast.parse(APP); node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name); lines=APP.splitlines(); return "\n".join(lines[node.lineno-1:node.end_lineno])
def test_e2e_disables_render_select_cache():
    block=_fn('_cacheable_query'); assert 'CUPNAVI_E2E' in block; assert 'return False' in block; assert 'startswith(("SELECT", "PRAGMA"))' in block
def test_production_cache_path_remains():
    assert '_RENDER_QUERY_CACHE' in _fn('all_rows'); assert '_RENDER_QUERY_CACHE' in _fn('one_row')
def test_same_sqlite_path_is_injected_into_streamlit_server():
    assert 'DB=Path("/tmp/cupnavi-streamlit-critical-journey.db")' in E2E; assert 'env["CUPNAVI_DB_PATH"]=str(DB)' in E2E
def test_submit_hardening_retained():
    assert 'submit.evaluate("el => el.click()")' in E2E
