from pathlib import Path
import ast
import sqlite3
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
E2E_PATH=ROOT/'e2e/test_streamlit_critical_journey.py'
E2E=E2E_PATH.read_text(encoding='utf-8')
APP=(ROOT/'app.py').read_text(encoding='utf-8')


def _load_wait_helper(db_path):
    tree=ast.parse(E2E)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='wait_for_persisted_tournament')
    module=ast.Module(body=[node],type_ignores=[])
    ast.fix_missing_locations(module)
    ns={'time':time,'sqlite3':sqlite3,'DB':db_path}
    exec(compile(module,str(E2E_PATH),'exec'),ns)
    return ns['wait_for_persisted_tournament']


def test_persistence_wait_handles_delayed_streamlit_commit(tmp_path):
    db=tmp_path/'delayed.sqlite'
    con=sqlite3.connect(db)
    con.execute('CREATE TABLE tournaments(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,environment_type TEXT)')
    con.commit(); con.close()

    def delayed_insert():
        time.sleep(.35)
        con=sqlite3.connect(db)
        con.execute("INSERT INTO tournaments(name,environment_type) VALUES('Delayed Cup','test')")
        con.commit(); con.close()

    thread=threading.Thread(target=delayed_insert)
    thread.start()
    row=_load_wait_helper(db)('Delayed Cup',timeout_ms=3000)
    thread.join()
    assert row is not None
    assert row[1]=='test'


def test_create_helper_polls_database_instead_of_immediate_read():
    start=E2E.index('def create_test_tournament_through_ui')
    end=E2E.index('\ndef ',start+5)
    block=E2E[start:end]
    assert 'row=wait_for_persisted_tournament(cup_name)' in block
    assert 'assert row is not None' not in block


def test_public_wait_reloads_transient_empty_public_render():
    start=E2E.index('def wait_for_public_cup')
    end=E2E.index('\ndef ',start+5)
    block=E2E[start:end]
    assert 'Ingen turnering är publicerad ännu.' in block
    assert 'page.reload(wait_until="domcontentloaded"' in block
    assert 'if value == cup_name:' in block


def test_e2e_mode_clears_render_local_cache_before_tournament_resolution():
    guard='if os.environ.get("CUPNAVI_E2E") == "1":\n    _clear_render_query_cache()'
    assert guard in APP
    assert APP.index(guard) < APP.index('view_mode = st.session_state["view_mode"]')
